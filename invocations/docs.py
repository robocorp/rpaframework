"""Common documentation related tasks"""

from pathlib import Path
import shutil
from datetime import datetime, date
from itertools import zip_longest

from jinja2 import Environment, FileSystemLoader

from invoke import task, Collection

from invocations import shell, config
from invocations.util import REPO_ROOT, MAIN_PACKAGE, safely_load_config


EXCLUDES = [
    "RPA.Cloud.AWS.textract*",
    "RPA.Cloud.Google.keywords*",
    "RPA.Cloud.objects*",
    "RPA.Desktop.keywords*",
    "RPA.Desktop.utils*",
    "RPA.Dialogs.*",
    "RPA.Email.common*",
    "RPA.PDF.keywords*",
    "RPA.Robocorp.utils*",
    "RPA.Windows.keywords*",
    "RPA.Windows.utils*",
    "RPA.core*",
    "RPA.recognition*",
    "RPA.scripts*",
]
DOCGEN_EXCLUDES = [f"--exclude {package}" for package in EXCLUDES]

DOCS_ROOT = REPO_ROOT / "docs"
DOCS_SOURCE_DIR = DOCS_ROOT / "source"
DOCS_BUILD_DIR = DOCS_ROOT / "build" / "html"
JINJA_TEMPLATE_DIR = DOCS_SOURCE_DIR / "template" / "jinja"
NOTES_DIR = DOCS_SOURCE_DIR / "releasenotes"
UPCOMING_NOTES_DIR = NOTES_DIR / "upcoming"
RELEASED_NOTES_DIR = NOTES_DIR / "released"


@task(pre=[config.install, config.install_node], aliases=["libdocs"])
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
        shell.sphinx(ctx, f"-b html -j auto {DOCS_SOURCE_DIR} {DOCS_BUILD_DIR}")
        shell.meta_tool(ctx, "rss")


@task(
    aliases=["local_docs", "host", "local"],
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


@task(aliases=["changelog"])
def print_changelog(ctx):
    """Prints changes in latest release."""
    shell.meta_tool(ctx, "changelog")


# Configure how this namespace will be loaded
ns = Collection("docs")


@task(
    aliases=["new_note", "note"], iterable=["name", "note", "issue_type", "issue_num"]
)
def new_release_note(
    ctx,
    version=None,
    release_date=None,
    name=None,
    note=None,
    issue_type=None,
    issue_num=None,
):
    """Creates a new release note based on a jinja template.

    You can supply the version number and release date or the
    current project version number and current date will be used.

    Release date must be provided in the format DD-MM-YYY, e.g.
    ``31-12-2022``. If your string fails to be parsed, the current
    date will be used.

    You can supply information about the notes by using the following
    parameters. Each can be repeated and the order is maintained, e.g.,
    the first ``name`` will be paired with the first ``note``.

    - ``name``: the name of the library the note relates to.
    - ``note``: the text of the note.
    - ``issue_type``: either ``pr`` or ``issue`` representing
      the GitHub PR or issue this note references.
    - ``issue_num``: the number of the GitHub PR or Issue referenced.

    If any key is not defined, a blank string will be used instead.
    """
    # only needed in this task
    from invocations import build

    if version is None:
        version = build.version(ctx)
    if release_date is None:
        release_date = date.today()
    else:
        release_date = datetime.strptime(release_date, "%d-%m-%Y")
    libraries = []
    for item in zip_longest(name, note, issue_type, issue_num):
        libraries.append(
            {
                "name": item[0],
                "note": item[1],
                "issue_type": item[2],
                "issue_num": item[3],
            }
        )

    env = Environment(loader=FileSystemLoader(JINJA_TEMPLATE_DIR))
    note_template = env.get_template("new_note.rst.jinja")
    new_note = note_template.render(
        version=version, release_date=release_date, libraries=libraries
    )
    filename = f"{release_date.strftime('%Y%m%d')}_new_releasenote.rst"
    new_file = NOTES_DIR / filename
    with new_file.open("w") as file:
        file.write(new_note)
    print(f"New file created at {new_file}, please check output before parsing")
