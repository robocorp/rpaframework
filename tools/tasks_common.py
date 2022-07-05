"""Common Invoke tasks.py helpers."""

import platform
import re
from glob import glob
from pathlib import Path


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


def poetry(ctx, command, **kwargs):
    kwargs.setdefault("echo", True)
    if platform.system() != "Windows":
        kwargs.setdefault("pty", True)

    return ctx.run(f"poetry {command}", **kwargs)


def replace_source(match):
    source_match = match.group(1).replace("\\", "/")
    source_result = re.split(r"(site-packages|src)/", source_match)[-1]
    return f'source="./{source_result}'


def modify_libspec_files(package_dir):
    files = glob(str(package_dir / "src" / "*.libspec"), recursive=False)
    pattern = r"source=\"([^\"]+)"
    for f in files:
        outfilename = f"{f}.modified"
        with open(f) as file_in:
            file_content = file_in.read()
            with open(outfilename, "w") as file_out:
                new_content = re.sub(
                    pattern, replace_source, file_content, 0, re.MULTILINE
                )
                file_out.write(new_content)
        target_file = package_dir / Path(f).name
        Path(f).unlink()
        try:
            Path(target_file).unlink()
        except FileNotFoundError:
            pass
        Path(outfilename).rename(target_file)


def libspec(ctx, *, package_dir):
    exclude_strings = " ".join(DOCGEN_EXCLUDES)
    command = (
        "run docgen --no-patches --relative-source --format libspec --output src "
        f"{exclude_strings} rpaframework"
    )
    poetry(ctx, command)
    modify_libspec_files(package_dir)


def cleanlibspec(_, *, package_dir):
    files = glob(str(package_dir / "*.libspec"), recursive=False)
    for f in files:
        Path(f).unlink()
