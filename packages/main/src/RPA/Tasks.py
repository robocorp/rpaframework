import base64
import copy
import json
import logging
import re
import string
import sys
from functools import partial
from pathlib import Path

import graphviz
from graphviz import ExecutableNotFound
from robot.errors import PassExecution
from robot.libraries.BuiltIn import BuiltIn


class SchemaError(Exception):
    """Error raised when violating schema."""


class Graph:
    """Task execution graph.

    Helper class which is used to store executed tasks and
    transitions between them, and render the relationships
    in a digraph.

    Creates a dot-notation file and rendered graph using graphviz.

    :param suite: Current suite running model
    """

    # Default render format
    FORMAT = "svg"

    # Default attributes
    GRAPH = {
        "rankdir": "LR",
    }
    NODE = {
        "shape": "box",
        "style": "rounded,filled",
        "margin": "0.15,0.1",
        "height": "0",
        "fontname": "Helvetica, Arial, sans-serif",
        "fontsize": "12",
    }

    # Start / end nodes
    TERMINATOR = {
        "shape": "oval",
        "style": "filled",
        "color": "#cccccc",
        "fillcolor": "#eeeeee",
        "fontcolor": "#0f0f0f",
    }

    # Node background/font colors
    COLORS = {
        "none": {"color": "#eeeeee", "fontcolor": "#0f0f0f"},
        "fail": {"color": "#d9534f", "fontcolor": "#ffffff"},
        "pass": {"color": "#5cb85c", "fontcolor": "#ffffff"},
        "warn": {"color": "#ec971f", "fontcolor": "#ffffff"},
    }

    def __init__(self, suite):
        #: Current suite
        self.suite = suite
        #: Task data by name
        self.tasks = {}
        #: Transition pairs between tasks
        self.edges = set()
        #: Current running task
        self.current = None
        #: Flag for successful end of process
        self.is_end = False

        self._parse_tasks(suite.tests)

    def _parse_tasks(self, tasks):
        """Parse tasks (nodes) and assign unique labels."""
        for position, task in enumerate(tasks):
            label = self._create_label(position)
            self.tasks[task.name] = {
                "name": task.name,
                "label": label,
                "result": "none",
                "doc": task.doc or task.name,
            }

    @staticmethod
    def _create_label(position):
        """Generate label for node, e.g. A, B, ..., AA, AB, AC, ..."""
        letters = string.ascii_uppercase

        label = ""
        while True:
            position, index = divmod(position, len(letters))
            label = letters[index] + label
            if not position:
                return label
            position -= 1

    def _create_graph(self, strip=True):
        """Create graphviz graph from current execution state."""
        graph = graphviz.Digraph(
            name=self.suite.name,
            format=self.FORMAT,
            graph_attr=self.GRAPH,
            node_attr=self.NODE,
        )

        # Start/end nodes
        graph.node("Start", **self.TERMINATOR)
        if self.is_end:
            graph.node("End", **self.TERMINATOR)

        # Task nodes
        for task in self.tasks.values():
            result = task.get("result", "none")
            if not (result == "none" and strip):
                colors = self.COLORS[result]
                graph.node(task["label"], task["name"], tooltip=task["doc"], **colors)

        # Edges
        for src, dst in self.edges:
            src = src if src == "Start" else self.tasks[src]["label"]
            dst = dst if dst == "End" else self.tasks[dst]["label"]
            graph.edge(src, dst)

        return graph

    def render_to_file(self, path, strip=True):
        """Render graphviz graph to given file."""
        path = Path(path)
        graph = self._create_graph(strip)
        return graph.render(filename=path.name, directory=path.parent)

    def render_to_bytes(self, strip=True):
        """Render graphviz graph to in-memory bytes object."""
        graph = self._create_graph(strip)
        return graph.pipe()

    def set_next(self, task):
        """Add transition between previous and next task."""
        previous, self.current = self.current, task.name
        if not previous:
            assert not self.edges, "Edges exist without previous task"
            previous = "Start"

        assert not self.is_end, f"Attempting to add task after end: {self.current}"
        assert self.current in self.tasks, f"Unknown task: {self.current}"

        pair = (previous, self.current)
        if pair not in self.edges:
            self.edges.add(pair)

    def set_result(self, result):
        """Set execution result for current task."""
        assert not self.is_end, "End already set"
        task = self.tasks[self.current]
        task["result"] = str(result).lower()

    def set_end(self):
        """Add final edge to End node."""
        assert not self.is_end, "End already set"
        self.edges.add((self.current, "End"))
        self.is_end = True


class Schema:
    """Task execution schema.

    A library for validating transitions betweens tasks,
    and evaluating possible schema-defined actions when
    these transitions are triggered.

    :param schema: content of schema JSON file
    :param names:  names of tasks in the current suite
    """

    def __init__(self, schema, names):
        #: Schema properties by task name
        self.tasks = {}
        #: Aliases for tasks
        self.aliases = {}
        #: First task in execution
        self.start = None
        #: Allowed end task(s)
        self.end = []

        self._parse_schema(schema, names)

    def _parse_schema(self, schema, names):
        """Parse schema file and validate contents.

        :param schema: content of schema file
        :param tasks:  tasks in suite execution
        """
        # First pass: Parse names and aliases
        for name, properties in schema.get("tasks", {}).items():
            assert name in names, f"Unknown task name: {name}"
            assert name not in self.tasks, f"Duplicate task name: {name}"

            # Flag for first task in the execution
            if properties.get("start", False):
                assert self.start is None, "Duplicate start task"
                self.start = name

            # Flag for allowed end task
            if properties.get("end", False):
                self.end.append(name)

            # Optional task alias
            alias = properties.get("alias")
            if alias:
                assert alias not in self.aliases, f"Duplicate alias: {alias}"
                self.aliases[alias] = name

            self.tasks[name] = properties

        # Second pass: Parse references to other tasks
        for name, properties in self.tasks.items():
            # Whitelist of allowed next tasks
            if "next" in properties:
                properties["next"] = [
                    self.resolve_reference(task) for task in properties["next"]
                ]
            # Actions for resolving the next task
            if "actions" in properties:
                properties["actions"] = [
                    self._create_action(action) for action in properties["actions"]
                ]

        # No start defined in schema, fallback to first in suite
        if not self.start:
            self.start = names[0]

    def _create_action(self, action):
        """Convert action definition in schema to callable."""
        assert "task" in action, "Next task undefined for action"
        task = self.resolve_reference(action["task"])

        callbacks = {
            "exception": self._action_exception,
            "condition": self._action_condition,
            "status": self._action_status,
        }

        operator = set(callbacks) & set(action)
        assert operator, f"Unknown action definition: {action}"
        assert len(operator) == 1, f"Multiple conditions in action: {action}"

        operator = operator.pop()
        callback = callbacks[operator]
        callback = partial(callback, action[operator])

        return callback, task

    def _action_exception(self, pattern, result):
        """Schema action: catch exception if it matches message pattern."""
        if result.passed:
            return False

        if not re.match(pattern, result.message):
            return False

        result.message = f"Transition: message = {pattern}"
        result.status = "PASS"
        return True

    def _action_condition(self, condition, result):
        """Schema action: evaluate Robot Framework expression."""
        if not result.passed and result.critical:
            return False

        if not BuiltIn().evaluate(condition):
            return False

        result.message = f"Transition: {condition}"
        return True

    def _action_status(self, status, result):
        """Schema action: compare test result to expected."""
        if result.status.upper() != status.upper():
            return False

        result.message = f"Transition: status == {status}"
        return True

    def resolve_reference(self, name):
        """Convert task reference to original name."""
        if name in self.tasks:
            return name
        elif name in self.aliases:
            return self.aliases[name]
        else:
            raise ValueError(f"Unknown task or alias: {name}")

    def validate(self, src, dst):
        """Validate transition between two tasks."""
        assert src in self.tasks, f"Unknown source task: {src}"

        # Optional end task validation
        if dst == "end":
            if self.end and src not in self.end:
                raise SchemaError("Unexpected end task")
            return

        if dst not in self.tasks:
            raise SchemaError(f"Destination '{dst}' not in schema")

        if "next" in self.tasks[src] and dst not in self.tasks[src]["next"]:
            raise SchemaError(f"Invalid transition '{src}' -> '{dst}'")

    def evaluate_actions(self, src, result):
        """Evaluate all actions for the source task,
        and return any potential triggered destination tasks.
        """
        actions = self.tasks[src].get("actions", [])

        # Evaluate all callbacks
        for action, task in actions:
            if action(result):
                return task

        # No conditions matched
        return None


class Tasks:
    """`Tasks` is a library for controlling task execution during a Robot Framework run.

    It allows conditional branching between tasks, loops and jumps, and optionally
    validating the execution through a schema file. It can also be used to
    visualize the tasks as a graph.

    .. _model:

    **Execution model**

    In a typical Robot Framework run, tasks are ordered linearly in a file and
    they're executed in definition order. Events that happen during
    the execution can not affect the order and only have the option to fail the task
    or continue as defined.

    Using the `Tasks` library, it's possible to change this model according
    to different states or inputs. The execution will start by running a single
    start task from the suite, and then according to user-defined keywords or
    schema rules select the next task. Any task which is defined in the same file
    can be used, and the same task can also be used multiple times during a single
    execution.

    .. _execution-example:

    Example:

    As an example, the following Robot Framework file describes a process where
    a task would have to be executed multiple times before a condition is reached.
    In a real-world scenario, these tasks would be more complicated, instead of just
    incrementing numbers.

    .. code-block:: robotframework

        *** Settings ***
        Library    RPA.Tasks

        *** Variables ***
        ${CURRENT}    ${1}
        ${TARGET}     ${5}

        *** Tasks ***
        Check loop condition
            Log    I'm trying to count to ${TARGET}
            Set next task if    ${CURRENT} >= ${TARGET}
            ...    Target reached
            ...    Increment current number

        This will not run
            Fail    This should never run

        Increment current number
            Set suite variable    ${CURRENT}    ${CURRENT + 1}
            Log    Number is now ${CURRENT}
            Jump to task    Check loop condition

        Target reached
            Log    Those are some good numbers!

    The execution for this example would go as follows:

    1. It starts from ``Check loop condition``, as it's the first task in the file.
    2. During the first task, the keyword ``Set next task if`` is called, which queues
       up the next task according to a condition.
    3. In the initial state, we have not reached the target number, and will next run
       the task ``Increment current number``.
    4. The second task executes normally and in the end jumps back to the first
       task using the keyword ``Jump to task``.
    5. The above sequence is repeated until the condition is met, and we move to
       the final task of the file. This final task does not schedule further tasks
       and the execution ends.

    You can also note the task ``This will not run``, which as the name implies
    is never executed, as no other task schedules or jumps to it.

    The console log from the above execution shows how the same task is executed
    multiple times:

    .. code-block:: console

        ==============================================================================
        Incrementing Process
        ==============================================================================
        #1   Check loop condition                                             | PASS |
        Transition: Set by keyword
        ------------------------------------------------------------------------------
        #2   Increment current number                                         | PASS |
        Transition: Set by keyword
        ------------------------------------------------------------------------------
        #3   Check loop condition                                             | PASS |
        Transition: Set by keyword
        ------------------------------------------------------------------------------
        #4   Increment current number                                         | PASS |
        Transition: Set by keyword
        ------------------------------------------------------------------------------
        #5   Check loop condition                                             | PASS |
        Transition: Set by keyword
        ------------------------------------------------------------------------------
        #6   Increment current number                                         | PASS |
        Transition: Set by keyword
        ------------------------------------------------------------------------------
        #7   Check loop condition                                             | PASS |
        Transition: Set by keyword
        ------------------------------------------------------------------------------
        #8   Increment current number                                         | PASS |
        Transition: Set by keyword
        ------------------------------------------------------------------------------
        #9   Check loop condition                                             | PASS |
        Transition: Set by keyword
        ------------------------------------------------------------------------------
        #10  Target reached                                                   | PASS |
        ------------------------------------------------------------------------------
        Incrementing Process:: [/graph_incrementing_process.svg]              | PASS |
        10 critical tasks, 10 passed, 0 failed
        10 tasks total, 10 passed, 0 failed
        ==============================================================================

    .. _graph:

    **Graph**

    A common way to document a process is through a directed graph. These graphs
    are usually drawn manually and describe the expected higher level steps.
    The actual implementation itself follows a different path through a graph,
    depending on inputs or implementation details. This library visualizes this
    execution graph using the `Graphviz <https://graphviz.org>`_ tool.

    After the execution is finished, it will create a
    `DOT <https://en.wikipedia.org/wiki/DOT_(graph_description_language)>`_ file
    and render it as an image. This image will automatically be appended
    to the suite's documentation field.

    **Requirements**

    Drawing the graph requires a working installation of
    `Graphviz <https://graphviz.org>`_. This can be installed through their
    website or by using `Conda <https://docs.conda.io/>`_.

    This requirement is optional for the functioning of this library, and will
    display a warning if the tool is not available. The visualization
    can be entirely disabled with the ``graph`` argument during library
    initialization.

    .. _schema:

    **Schema**

    There is an option to define a schema file for the suite, which is written in JSON.
    This file will be used to validate the actual execution and fail it if an unexpected
    transition between tasks happens. It can also define rules for selecting the next
    task, which allows separating the task and process definitions.

    Example:

    The execution-example shown previously used keywords to control
    the execution. This can also be done using the following schema:

    .. code-block:: json

        {
            "tasks": {
                "Check loop condition": {
                    "alias": "check",
                    "start": true,
                    "next": [
                        "increment",
                        "target"
                    ],
                    "actions": [
                        {
                            "condition": "$CURRENT >= $TARGET",
                            "task": "target"
                        },
                        {
                            "condition": "$CURRENT < $TARGET",
                            "task": "increment"
                        }
                    ]
                },
                "Increment current number": {
                    "alias": "increment",
                    "next": [
                        "check"
                    ],
                    "actions": [
                        {
                            "status": "PASS",
                            "task": "check"
                        }
                    ]
                },
                "Target reached": {
                    "alias": "target",
                    "end": true,
                    "next": []
                }
            }
        }

    This has the added benefit of protecting against implementation errors,
    as the library will validate the start and end tasks, and transitions between
    different tasks.

    After this schema has been taken into use, the aforementioned example
    will reduce to the following:

    .. code-block:: robotframework

        *** Settings ***
        Library    RPA.Tasks    schema=counter-schema.json

        *** Variables ***
        ${CURRENT}    ${1}
        ${TARGET}     ${5}

        *** Tasks ***
        Check loop condition
            Log    I'm trying to count to ${TARGET}

        This will not run
            Fail    This should never run

        Increment current number
            Set suite variable    ${CURRENT}    ${CURRENT + 1}
            Log    Number is now ${CURRENT}

        Target reached
            Log    Those are some good numbers!

    **Format**

    The current format is JSON with the following structure:

    .. code-block:: javascript

        {
            "tasks": {
                [name: string]: {
                    "alias": string,
                    "start": boolean,
                    "end": boolean,
                    "next": string[],
                    "actions": action[],
                }
            }
        }

    Each schema is a map of tasks with various properties. The keys must
    match the task names in the Robot Framework file definition. All properties
    inside the task are optional.

    The available properties and their uses:

    - *alias*:   Define a short name for the task, which can be used as a reference
                 inside the schema.
    - *start*:   Start task for execution. There can be only one task with this
                 enabled. If not defined, will default to first task in the file.
    - *end*:     Valid end task for execution. There can be multiple tasks with this
                 enabled. Fails the execution if this is defined for any task and the
                 execution stops in a non-end task.
    - *next*:    List of valid tasks to transition to from this task. Supports
                 alias definitions.
    - *actions*: List of actions that are executed at the end of the task.
                 See section below for details.

    The types of actions:

    - *exception*: Set the next task if a matching exception occurs.
                   Matches the exception message as regex.
    - *condition*: Set the next task if a conditional expression is true.
                   Allows using Robot Framework variables.
    - *status*:    Set the next task if the current task's result matches,
                   e.g. PASS or FAIL.

    Examples of actions:

    .. code-block:: json

        [
            {"exception": ".*ValueError.*", "task": "Invalid input values"},
            {"condition": "$ATTEMPTS > 10", "task": "Too many attempts"},
            {"status": "PASS", "task": "Success state"}
        ]
    """  # noqa: E501

    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    ROBOT_LIBRARY_DOC_FORMAT = "REST"
    ROBOT_LISTENER_API_VERSION = 3

    TAG_NONCRITICAL = "tasks-schema-noncritical"

    def __init__(
        self, execution_limit=1024, schema=None, graph=True, graph_inline=True
    ):
        """There are a few arguments for controlling the Tasks library.

        :param execution_limit: Maximum number of tasks to run in suite,
                                used to prevent infinite loops
        :param schema:          Path to optional schema file
        :param graph:           Render execution result as graph using graphviz
        :param graph_inline:    Inline graph into log, instead of saving as file
        """
        self.ROBOT_LIBRARY_LISTENER = self

        #: Current task execution count
        self.count = 0
        #: Maximum task execution
        self.limit = int(execution_limit)
        #: Current suite running model
        self.suite = None
        #: Original task running models
        self.tasks = None
        #: Current running task
        self.current = None
        #: Next scheduled task
        self.next = None
        #: Task execution schema
        self.schema = None
        self.schema_path = schema
        #: Task execution graph
        self.graph = None
        self.graph_options = {"enabled": graph, "inline": graph_inline}

    def _load_schema(self):
        """Load schema from file, if defined."""
        self.schema = None
        if not self.schema_path:
            return

        with open(self.schema_path) as fd:
            data = json.load(fd)
            names = [task.name for task in self.tasks]
            self.schema = Schema(data, names)

    def _task_by_name(self, name):
        """Find task execution object by shortname."""
        for task in self.tasks:
            if task.name == name:
                return task

        raise ValueError(f"Task not found: {name}")

    def _find_next_task(self, result):
        """Resolve the next task based on the previous result."""
        # TODO: Move all result object modifying here
        task = None

        try:
            if self.next:
                task = self.next
                result.message = "Transition: Set by keyword"
            elif self.schema:
                task = self.schema.evaluate_actions(self.current.name, result)
                task = self._task_by_name(task) if task else None
                result.tags.add(self.TAG_NONCRITICAL)  # Schema overrides status

            if self.schema:
                name = task.name if task else "end"
                self.schema.validate(self.current.name, name)

        except SchemaError as err:
            logging.error(err)
            result.status = "FAIL"

        finally:
            self.next = None

        return task, result

    def _append_task(self, task):
        """Append new copy of task to execution queue."""
        self.count += 1

        # Ensure we don't edit original model
        name = "#{:<3} {}".format(self.count, task.name)
        copied = task.copy(name=name)
        self.suite.tests.append(copied)
        self.current = task

        # Show transition between tasks
        self.graph.set_next(task)

    def _start_suite(self, data, result):
        """Robot listener method, called on suite start.
        Copies original tasks to be used as source for scheduling.
        """
        self.count = 0
        self.next = None
        self.suite = data
        self.tasks = copy.deepcopy(self.suite.tests)
        self.graph = Graph(self.suite)

        self.suite.tests.clear()

        try:
            self._load_schema()
        except Exception as exc:  # pylint: disable=broad-except
            logging.error("Schema parsing failed: %s", exc)
            sys.exit(1)

        if self.schema:
            self._append_task(self._task_by_name(self.schema.start))
        else:
            self._append_task(self.tasks[0])

        # Set a unique non-critical tag to be used when
        # execution should continue after a FAIL status
        root = result
        while root.parent:
            root = root.parent
        root.set_criticality(non_critical_tags=[self.TAG_NONCRITICAL])

    def _end_suite(self, data, result):
        """Render graph of suite execution to the documentation field."""
        del result

        if not self.graph_options.get("enabled", True):
            return

        try:
            if self.graph_options.get("inline", True):
                # Render as inline data URI
                data = self.graph.render_to_bytes()
                src = "data:image/svg+xml;base64,{}".format(
                    base64.b64encode(data).decode("utf-8")
                )
            else:
                # Render to file
                dirname = BuiltIn().get_variable_value("${OUTPUT_DIR}")
                filename = "graph_{}".format(data.name.lower().replace(" ", "_"))

                path = Path(dirname, filename)
                src = self.graph.render_to_file(str(path))

            BuiltIn().set_suite_documentation(f"[{src}|Graph]", append=True)
        except ExecutableNotFound as err:
            logging.warning("Graphviz executable not found: %s", err)

    def _end_test(self, data, result):
        """Robot listener method, called on test end.
        Rewrites next executable task, if overriden by keywords.
        Appends incrementing number to prevent task naming conflicts.
        """
        del data

        task, result = self._find_next_task(result)

        if not result.passed:
            self.graph.set_result("fail")
            if result.critical:
                return
        else:
            self.graph.set_result("pass")

        if not task:
            self.graph.set_end()
            return
        else:
            self._append_task(task)

    def set_next_task(self, name):
        """Set the next task to be executed.
        Should be a task in the same suite.

        :param name: Name of next task
        """
        task = self._task_by_name(name)

        if self.next:
            logging.warning(
                "Overwriting scheduled task '%s' with '%s'", self.next.name, task.name
            )

        logging.info("Scheduling task: %s", task.name)
        assert self.count < self.limit, "Reached task execution limit"

        if self.schema:
            self.schema.validate(self.current.name, task.name)

        self.next = task

    def set_next_task_if(self, condition, name, default=None):
        """Set the next task according to the condition.
        If no default is given, does not modify execution order.

        :param condition: Condition expression to evaluate
        :param name:      Name of next task, if successful
        :param default:   Name of next task, if unsuccessful
        """
        is_true = (
            BuiltIn().evaluate(condition)
            if isinstance(condition, str)
            else bool(condition)
        )

        logging.info("Condition: %s -> %s", condition, is_true)
        task = name if is_true else default

        if task:
            self.set_next_task(task)

    def jump_to_task(self, name):
        """Jump directly to given task, skipping the rest of the task
        execution. If run inside a teardown, also skips the rest of the
        teardown sequence.
        """
        self.set_next_task(name)
        raise PassExecution(f"Jumping to: {self.next}")

    def jump_to_task_if(self, condition, name, default=None):
        """Jump directly to given task according to the condition."""
        self.set_next_task_if(condition, name, default)
        if self.next:
            raise PassExecution(f"Jumping to: {self.next}")

    def set_next_task_if_keyword_fails(self, task, keyword, *args):
        """Executes given keyword and sets the next task if it fails."""
        success = BuiltIn().run_keyword_and_return_status(keyword, *args)
        if not success:
            self.set_next_task(task)

    def set_next_task_if_keyword_succeeds(self, task, keyword, *args):
        """Executes given keyword and sets the next task if it succeeds."""
        success = BuiltIn().run_keyword_and_return_status(keyword, *args)
        if success:
            self.set_next_task(task)

    def jump_to_task_if_keyword_fails(self, task, keyword, *args):
        """Executes given keyword and jumps to given task if it fails."""
        success = BuiltIn().run_keyword_and_return_status(keyword, *args)
        if not success:
            self.jump_to_task(task)

    def jump_to_task_if_keyword_succeeds(self, task, keyword, *args):
        """Executes given keyword and jumps to given task if it succeeds."""
        success = BuiltIn().run_keyword_and_return_status(keyword, *args)
        if success:
            self.jump_to_task(task)
