#!/usr/bin/env python3
import subprocess
from pathlib import Path


def run(*args):
    return subprocess.check_output(args).decode().strip()


def main():
    name = Path.cwd().name
    version = run("poetry", "version", "-s")
    tag = f"{name}_{version}"

    print(f"Tagging release: {tag}")
    run("git", "tag", "-a", tag, "-m", f"Release {version} for package {name}")
    run("git", "push", "origin", f"refs/tags/{tag}")


if __name__ == "__main__":
    main()
