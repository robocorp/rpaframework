#!/usr/bin/env python3

import platform
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


def main():
    branch = run("git", "rev-parse", "--abbrev-ref", "HEAD")
    if branch != "master":
        print("Current branch not 'master', skipping tag")
        return

    name = Path.cwd().name
    version = run("poetry", "version", "-s")
    tag = f"{name}_{version}"

    print(f"Tagging release: {tag}")
    run("git", "tag", "-a", tag, "-m", f"Release {version} for package {name}")
    run("git", "push", "origin", f"refs/tags/{tag}")


if __name__ == "__main__":
    main()
