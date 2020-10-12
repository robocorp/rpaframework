#####
Tasks
#####

.. contents:: Table of Contents
   :local:
   :depth: 2

***********
Description
***********

`Tasks` is a library for controlling task execution during a Robot Framework run.
It allows conditional branching between tasks, loops and jumps, and optionally
validating the execution through a :ref:`schema` file. It can also be used to
visualize the tasks as a :ref:`graph`.

.. _model:

Execution model
===============

In a typical Robot Framework run, tasks are ordered linearly in a file and
they're executed in definition order. Events that happen during
the execution can not affect the order and only have the option to fail the task
or continue as defined.

Using the `Tasks` library, it's possible to change this model according
to different states or inputs. The execution will start by running a single
start task from the suite, and then according to user-defined keywords or
schema rules select the next task. Any task which is defined in the same file
can be used, and the same task can also be used multiple times during a single execution.

.. _execution-example:

Example
-------

As an example, the following Robot Framework file describes a process where
a task would have to be executed multiple times before a condition is reached.
In a real-world scenario, these tasks would be more complicated, instead of just
incrementing numbers.

.. code-block:: robotframework
    :linenos:

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
2. During the first task, the keyword ``Set next task if`` is called, which queues up the next task according to a condition.
3. In the initial state, we have not reached the target number, and will next run the task ``Increment current number``.
4. The second task executes normally and in the end jumps back to the first task using the keyword ``Jump to task``.
5. The above sequence is repeated until the condition is met, and we move to the final task of the file. This final task does not schedule further tasks and the execution ends.

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

Graph
=====

A common way to document a process is through a directed graph. These graphs
are usually drawn manually and describe the expected higher level steps.
The actual implementation itself follows a different path through a graph,
depending on inputs or implementation details. This library visualizes this
execution graph using the `Graphviz <https://graphviz.org>`_ tool.

After the execution is finished, it will create a
`DOT <https://en.wikipedia.org/wiki/DOT_(graph_description_language)>`_ file
and render it as an image. This image will automatically be appended
to the suite's documentation field.

.. image:: /attachments/graph.png

The above graph is a visualization of the tasks defined in the previous
:ref:`execution-example`.

Requirements
------------

Drawing the graph requires a working installation of
`Graphviz <https://graphviz.org>`_. This can be installed through their
website or by using `Conda <https://docs.conda.io/>`_.

This requirement is optional for the functioning of this library, and will
display a warning if the tool is not available. The visualization
can be entirely disabled with the ``graph`` argument during library
initialization.

.. _schema:

Schema
======

There is an option to define a schema file for the suite, which is written in JSON.
This file will be used to validate the actual execution and fail it if an unexpected
transition between tasks happens. It can also define rules for selecting the next
task, which allows separating the task and process definitions.

Example
-------

The :ref:`execution-example` shown previously used keywords to control
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
    :linenos:

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

Format
------

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

- *alias*:   Define a short name for the task, which can be used as a reference inside the schema.
- *start*:   Start task for execution. There can be only one task with this enabled. If not defined, will default to first task in the file.
- *end*:     Valid end task for execution. There can be multiple tasks with this enabled. Fails the execution if this is defined for any task and the execution stops in a non-end task.
- *next*:    List of valid tasks to transition to from this task. Supports alias definitions.
- *actions*: List of actions that are executed at the end of the task. See section below for details.

The types of actions:

- *exception*: Set the next task if a matching exception occurs. Matches the exception message as regex.
- *condition*: Set the next task if a conditional expression is true. Allows using Robot Framework variables.
- *status*:    Set the next task if the current task's result matches, e.g. PASS or FAIL.

Examples of actions:

.. code-block:: json

    [
        {"exception": ".*ValueError.*", "task": "Invalid input values"},
        {"condition": "$ATTEMPTS > 10", "task": "Too many attempts"},
        {"status": "PASS", "task": "Success state"}
    ]


*****************
API Documentation
*****************

.. toctree::
   :maxdepth: 1

   ../../libdoc/Tasks.rst
