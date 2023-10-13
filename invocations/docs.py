"""Common documentation related tasks"""
import json
import re
import shutil
from pathlib import Path

from invoke import Collection, Result, task

from invocations import config, shell
from invocations.util import MAIN_PACKAGE, REPO_ROOT, safely_load_config


EXCLUDES = [
    "RPA.Cloud.AWS.textract*",
    "RPA.Cloud.Google.keywords*",
    "RPA.Cloud.objects*",
    "RPA.Desktop.keywords*",
    "RPA.Desktop.utils*",
    "RPA.Dialogs.*",
    "RPA.Assistant.*",
    "RPA.Email.common*",
    "RPA.PDF.keywords*",
    "RPA.Robocorp.utils*",
    "RPA.Windows.keywords*",
    "RPA.Windows.utils*",
    "RPA.application*",
    "RPA.core*",
    "RPA.recognition*",
    "RPA.scripts*",
]
DOCGEN_EXCLUDES = [f"--exclude {package}" for package in EXCLUDES]

DOCS_ROOT = REPO_ROOT / "docs"
DOCS_SOURCE_DIR = DOCS_ROOT / "source"
DOCS_BUILD_DIR = DOCS_ROOT / "build" / "html"

FAILURE_TRACES = ["WARNING: autodoc:"]


@task(pre=[config.install, config.install_node], aliases=("libdocs",))
def build_libdocs(ctx):
    """Generates library specification and documentation using ``docgen``"""
    libspec_promise = shell.docgen(
        ctx,
        "rpaframework",
        "--no-patches",
        "--format libspec",
        "--output docs/source/libspec/",
        *DOCGEN_EXCLUDES,
        asynchronous=True,
    )
    html_promise = shell.docgen(
        ctx,
        "rpaframework",
        "--template docs/source/template/libdoc/libdoc.html",
        "--format html",
        "--output docs/source/include/libdoc/",
        *DOCGEN_EXCLUDES,
        asynchronous=True,
    )
    json_promise = shell.docgen(
        ctx,
        "rpaframework",
        "--no-patches",
        "--format json-html",
        "--output docs/source/json/",
        *DOCGEN_EXCLUDES,
        asynchronous=True,
    )
    libspec_promise.join()
    html_promise.join()
    json_promise.join()
    shutil.copy2(
        "docs/source/template/iframeResizer.contentWindow.map",
        "docs/source/include/libdoc/",
    )


def _check_documentation_build(run_result: Result):
    lines = f"{run_result.stdout}\n{run_result.stderr}".splitlines()
    for line in lines:
        if any(trace in line for trace in FAILURE_TRACES):
            raise RuntimeError(line)


@task(pre=[config.install, build_libdocs], default=True, aliases=("build",))
def build_docs(ctx):
    """Builds documentation locally. These can then be browsed directly
    by going to ./docs/build/html/index.html or using ``invoke local-docs``
    and navigating to localhost:8000 in your browser.

    If you are developing documentation for an optional package, you must
    use the appropriate ``invoke install-local`` command first.

    Expects an invoke configuration item at ``docs.source`` and
    ``docs.target``, if they are missing, they are set to default.
    """
    if not getattr(ctx, "is_meta", False):
        return

    docs_source = Path(safely_load_config(ctx, "ctx.docs.source", DOCS_SOURCE_DIR))
    docs_target = Path(safely_load_config(ctx, "ctx.docs.target", DOCS_BUILD_DIR))
    main_package = Path(safely_load_config(ctx, "ctx.main_package", MAIN_PACKAGE))
    shell.sphinx(ctx, f"-M clean {docs_source} {docs_target}")
    shell.meta_tool(
        ctx,
        "todos",
        main_package / "src",
        docs_source / "contributing" / "todos.rst",
    )
    shell.meta_tool(
        ctx,
        "merge",
        docs_source / "json",
        docs_source / "include" / "latest.json",
    )
    run_result = shell.sphinx(ctx, f"-b html -j auto {docs_source} {docs_target}")
    _check_documentation_build(run_result)
    shell.meta_tool(ctx, "rss")


@task(pre=[config.install], aliases=("python-markdown",))
def build_python_markdown(ctx):
    """Build Markdown documentation for Python APIs of libraries.
    Used for ingesting API documentation into Robocorp Docs.
    """
    if not getattr(ctx, "is_meta", False):
        return

    docs_source = Path(safely_load_config(ctx, "ctx.docs.source", DOCS_SOURCE_DIR))
    docs_target = Path(safely_load_config(ctx, "ctx.docs.target", DOCS_ROOT / "build" / "markdown"))

    # shell.sphinx(ctx, f"-M clean {docs_source} {docs_target}")
    shell.sphinx(ctx, f"-b markdown -D libdoc_markdown=True {docs_source} {docs_target}")

    # Build index of folder name to module name
    module_index: dict[str, str] = {}
    for library_path in (DOCS_SOURCE_DIR / "libraries").iterdir():
        if not library_path.is_dir():
            continue

        python_path = library_path / "python.rst"
        if not python_path.is_file():
            print(f"Missing python API documentation: {library_path}")
            continue

        with open(python_path, "r", encoding="utf-8") as fd:
            match = re.search(r"\.\.\s+auto(module|class)::\s+(.+)", fd.read())
            if match:
                module_index[library_path.name] = match.group(2)
            else:
                print(f"Missing automodule/autoclass directive: {python_path}")

    # Read generated markdown
    libraries = []
    for library_path in (docs_target / "libraries").iterdir():
        if not library_path.is_dir():
            continue

        python_path = library_path / "python.md"
        if not python_path.is_file():
            continue

        python_module = module_index.get(library_path.name)
        if not python_module:
            raise RuntimeError(f"Missing module name: {library_path}")

        with open(python_path, "r", encoding="utf-8") as fd:
            entry = {"module": python_module, "markdown": fd.read()}
            libraries.append(entry)

    # Create database file
    output = DOCS_BUILD_DIR / "python.json"
    with open(output, "w", encoding="utf-8") as fd:
        print(f"Writing markdown output: {output}")
        json.dump(libraries, fd, indent=2)


@task(
    aliases=("local_docs", "host", "local"),
    help={
        "disown": (
            "Starts the HTTP server and disowns the thread, "
            "letting it continue to run and returning to the shell."
        )
    },
)
def host_local_docs(ctx, disown=False):
    """Hosts library documentation on a local http server. Navigate to
    localhost:8000 to browse."""
    print(
        "Starting documentation server, navigate to "
        + "http://localhost:8000/ to browse. "
        + "Send a Keyboard Interrupt to exit."
        if not disown
        else ""
    )
    shell.run_in_venv(
        ctx, "python", "-u -m http.server -d docs/build/html/", disown=disown
    )


@task(aliases=("changelog",))
def print_changelog(ctx):
    """Prints changes in latest release."""
    shell.meta_tool(ctx, "changelog")


# Configure how this namespace will be loaded
ns = Collection("docs")
