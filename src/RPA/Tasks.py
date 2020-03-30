import copy
import json
import logging
import re
import string
import sys
from functools import partial

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

    def render(self, filename=None, dirname=None, strip=True):
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

        return graph.render(filename=filename, directory=dirname)

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
        if result.status != status.upper():
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
    """`Tasks` is a Robot Framework library for controlling
    task execution inside a suite. It allows changing the next scheduled task
    or jumping immediately to other tasks by using the keywords it provides.

    If ``Graphviz`` is available, it will also create a directed graph
    to visualize connected tasks, which is visible in the suite documentation
    field of the test log.
    """

    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    ROBOT_LISTENER_API_VERSION = 3

    def __init__(self, execution_limit=1024, schema=None, graph=True):
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
        self.render = graph

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
        del result

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

    def _end_suite(self, data, result):
        """Render graph of suite execution to the documentation field."""
        del result

        if not self.render:
            return

        filename = "graph_{}".format(data.name.lower().replace(" ", "_"))
        dirname = BuiltIn().get_variable_value("${OUTPUT_DIR}")

        try:
            path = self.graph.render(filename, dirname)
            BuiltIn().set_suite_documentation(f"[{path}|Graph]", append=True)
        except ExecutableNotFound as err:
            logging.warning("Graphviz executable not found: %s", err)

    def _end_test(self, data, result):
        """Robot listener method, called on test end.
        Rewrites next executable task, if overriden by keywords.
        Appends incrementing number to prevent task naming conflicts.
        """
        del data

        task, result = self._find_next_task(result)

        if not result.passed and result.critical:
            self.graph.set_result("fail")
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
