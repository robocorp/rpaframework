"""Common documentation related tasks"""
from pathlib import Path
import shutil

from invoke import task, Collection

from invocations import shell, config
from invocations.util import REPO_ROOT

EXCLUDES = [
    "RPA.scripts*",
    "RPA.core*",
    "RPA.recognition*",
    "RPA.Desktop.keywords*",
    "RPA.Desktop.utils*",
    "RPA.PDF.keywords*",
    "RPA.Cloud.objects*",
    "RPA.Cloud.Google.keywords*",
    "RPA.Robocorp.utils*",
    "RPA.Dialogs.*",
    "RPA.Windows.keywords*",
    "RPA.Windows.utils*",
    "RPA.Cloud.AWS.textract*",
]
DOCGEN_EXCLUDES = [f"--exclude {package}" for package in EXCLUDES]

DOCS_ROOT = REPO_ROOT / "docs"
DOCS_SOURCE_DIR = DOCS_ROOT / "source"
DOCS_BUILD_DIR = DOCS_ROOT / "build" / "html"


@task(pre=[config.install])
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


@task(pre=[config.install, build_libdocs], default=True, aliases=["build"])
def build_docs(ctx):
    """Builds documentation locally. These can then be browsed directly
    by going to ./docs/build/html/index.html or using ``invoke local-docs``
    and navigating to localhost:8000 in your browser.

    If you are developing documentation for an optional package, you must
    use the appropriate ``invoke install-local`` command first.

    Expects an invoke configuration item at ``docs.source`` and
    ``docs.target``, if they are missing, they are set to default.
    """
    if getattr(ctx, "is_meta", False):
        try:
            docs_source = Path(ctx.docs.source)
        except AttributeError:
            docs_source = DOCS_SOURCE_DIR
        try:
            docs_target = Path(ctx.docs.target)
        except AttributeError:
            docs_target = DOCS_BUILD_DIR
        shell.sphinx(ctx, f"-M clean {docs_source} {docs_target}")
        shell.meta_tool(
            ctx, "todos", "packages/main/src", "docs/source/contributing/todos.rst"
        )
        shell.meta_tool(
            ctx,
            "merge",
            "docs/source/json/",
            "docs/source/include/latest.json",
        )
        shell.sphinx(ctx, f"-b html -j auto {DOCS_SOURCE_DIR} {DOCS_BUILD_DIR}")
        shell.meta_tool(ctx, "rss")


@task(aliases=["local_docs"])
def host_local_docs(ctx):
    """Hosts library documentation on a local http server. Navigate to
    localhost:8000 to browse."""
    shell.run_in_venv(ctx, "python -m http.server -d docs/build/html/")


@task(aliases=["changelog"])
def print_changelog(ctx):
    """Prints changes in latest release."""
    shell.meta_tool(ctx, "changelog")


# Configure how this namespace will be loaded
ns = Collection("docs")
