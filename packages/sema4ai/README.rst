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

- **Workspace files.** On the platform the files of a project are mounted into
  the sandbox as a normal directory. The library lists, reads, writes, moves,
  copies and deletes them with workspace-relative paths, never leaves the
  workspace, and by default leaves platform-managed content under
  ``.blockparty`` untouched.
- **Projects.** ``List Projects`` and ``Get Project`` return the projects the
  current run can see, through the platform SDK.

Both parts are meant for code running on the platform. Access from outside the
platform is planned and not part of this version.

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

Outside the platform, point the library at a local directory to develop and
test: ``Sema4AI(workspace_root="path/to/copy")``.
