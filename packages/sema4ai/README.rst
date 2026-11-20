rpaframework-sema4ai
====================

This package is a part of the `RPA Framework`_ project. It contains the
``RPA.Sema4AI`` library for automation code that works with a project on the
`Sema4.ai`_ cloud platform.

.. _RPA Framework: https://rpaframework.org
.. _Sema4.ai: https://sema4.ai

Version 3 is a new library for the Sema4.ai cloud platform. Versions 1 and 2 of
this package talked to the Sema4.ai Agent API; that library was retired with
2.1.0 and shares only the name with this one. Pin ``rpaframework-sema4ai==2.1.0`` if you still need it.

What it does
------------

- **Workspace files.** The library lists, reads, writes, moves, copies and
  deletes the files of a project with workspace-relative paths. It never leaves
  the workspace, and by default leaves platform-managed content under
  ``.blockparty`` untouched.

  - *On the platform* the files are mounted into the sandbox as a normal
    directory, and no configuration is needed.
  - *Outside the platform* (a robot on a Control Room worker, a developer
    machine) the same keywords use the project's REST API with a project API
    key, which is created in the project's settings.

- **Projects.** ``List Projects`` and ``Get Project`` return the projects the
  current run can see, through the platform SDK. These work on the platform
  only.

Installation
------------

.. code-block:: bash

    pip install rpaframework-sema4ai

The package has no runtime dependencies. A Sema4.ai project has no network
access by default, so installing from PyPI inside a sandbox needs the project's
network policy to allow it.

Usage
-----

Python:

.. code-block:: python

    from RPA.Sema4AI import Sema4AI

    sema4 = Sema4AI()
    sema4.write_workspace_file("reports/summary.md", "All 12 invoices matched.")
    for file in sema4.list_workspace_files("reports"):
        print(file["path"], file["size"])

Robot Framework:

.. code-block:: robotframework

    *** Settings ***
    Library    RPA.Sema4AI

    *** Tasks ***
    Write a report into the project
        Write Workspace File    reports/summary.md    All 12 invoices matched.
        ${files}=    List Workspace Files    reports

Outside the platform, connect to a project with its API key. Read the key from
a vault instead of writing it into the robot:

.. code-block:: python

    from RPA.Robocorp.Vault import Vault
    from RPA.Sema4AI import Sema4AI

    secret = Vault().get_secret("sema4_project")
    sema4 = Sema4AI()
    sema4.connect_to_sema4_project(
        secret["project_id"], secret["api_key"], base_url="https://us3.sema4.ai"
    )
    print(sema4.read_workspace_file("reports/summary.md"))

The same settings can come from the environment variables ``SEMA4AI_BASE_URL``,
``SEMA4AI_PROJECT_ID`` and ``SEMA4AI_API_KEY``.

To develop and test against a local copy of a workspace, point the library at a
directory: ``Sema4AI(workspace_root="path/to/copy")``.
