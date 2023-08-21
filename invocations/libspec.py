"""Common libspec related tasks"""

import re
from glob import glob
from pathlib import Path

from invoke import Collection, task

from invocations import config, shell
from invocations.docs import DOCGEN_EXCLUDES


def _replace_source(match: re.Match):
    source_match = match.group(1).replace("\\", "/")
    source_result = re.split(r"(site-packages|src)/", source_match)[-1]
    return f'source="./{source_result}'


def _modify_libspec_files(package_dir: Path):
    files = glob(str(package_dir / "src" / "*.libspec"), recursive=False)
    pattern = r"source=\"([^\"]+)"
    for f in files:
        outfilename = f"{f}.modified"
        with open(f) as file_in:
            file_content = file_in.read()
            with open(outfilename, "w") as file_out:
                new_content = re.sub(
                    pattern, _replace_source, file_content, 0, re.MULTILINE
                )
                file_out.write(new_content)
        target_file = package_dir / Path(f).name
        Path(f).unlink()
        try:
            Path(target_file).unlink()
        except FileNotFoundError:
            pass
        Path(outfilename).rename(target_file)


@task(
    pre=[config.install],
    aliases=["build"],
    default=True,
    help={
        "package-dir": (
            "You can set a specific path to use as the package "
            "directory. This is normally set automatically as part "
            "of this invocation collection."
        )
    },
)
def build_libspec(ctx, package_dir=None):
    """Create library spec files for the package with docgen. If
    ran at the meta-package level, builds libspecs for all pacakges.
    """
    if getattr(ctx, "is_meta", False):
        shell.invoke_each(ctx, "libspec.build")
    else:
        if package_dir is None:
            package_dir = Path(ctx.package_dir)
        exclude_strings = " ".join(DOCGEN_EXCLUDES)
        command = (
            "--no-patches --relative-source --format libspec --output src "
            f"{exclude_strings} rpaframework"
        )
        shell.run_in_venv(ctx, "docgen", command)
        _modify_libspec_files(package_dir)


@task(
    aliases=["clean"],
    help={
        "package-dir": (
            "You can set a specific path to use as the package "
            "directory. This is normally set automatically as part "
            "of this invocation collection."
        )
    },
)
def clean_libspec(ctx, package_dir=None):
    """Remove all generated ``*.libspec`` files."""
    if getattr(ctx, "is_meta", False):
        shell.invoke_each(ctx, "libspec.clean")
    else:
        if package_dir is None:
            package_dir = Path(ctx.package_dir)
        files = glob(str(package_dir / "*.libspec"), recursive=False)
        for f in files:
            Path(f).unlink()


# Configure how this namespace will be loaded
ns = Collection("libspec")
