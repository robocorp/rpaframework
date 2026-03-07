#!/usr/bin/env python3

import platform
import re
import subprocess
from pathlib import Path


def run(*args):
    run_process = lambda params: subprocess.check_output(params).decode().strip()

    try:
        return run_process(args)
    except FileNotFoundError:
        if platform.system() != "Windows":
            raise

        # Edge-case for Windows 11 with different paths. (solved by absolute path)
        abs_path = run_process(["where", args[0]]).splitlines()[-1]
        return run_process((abs_path,) + args[1:])


def read_pyproject_field(field: str) -> str:
    pyproject = Path.cwd() / "pyproject.toml"
    content = pyproject.read_text(encoding="utf-8")
    match = re.search(rf'^{field}\s*=\s*"([^"]+)"', content, re.MULTILINE)
    if not match:
        raise RuntimeError(f"Could not find '{field}' in pyproject.toml")
    return match.group(1)


def main():
    branch = run("git", "rev-parse", "--abbrev-ref", "HEAD")
    if branch != "master":
        print("Current branch not 'master', skipping tag")
        return

    name = read_pyproject_field("name")
    version = read_pyproject_field("version")
    tag = f"{name}-{version}"

    print(f"Tagging release: {tag}")
    run("git", "tag", "-a", tag, "-m", f"Release {version} for package {name}")
    run("git", "push", "origin", f"refs/tags/{tag}")


if __name__ == "__main__":
    main()
