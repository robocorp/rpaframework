#!/usr/bin/env python3
import sys
import toml
from pathlib import Path

ROOT = Path(Path(__file__).parent, "..").resolve()
META = "pyproject.toml"
PKGS = "packages/*/pyproject.toml"


def load_meta():
    with open(Path(ROOT, META)) as fd:
        pyproject = toml.load(fd)
        return pyproject["tool"]["poetry"]


def load_packages():
    pkgs = []
    for pkg in Path(ROOT).glob(PKGS):
        with open(pkg) as fd:
            pyproject = toml.load(fd)
            pkgs.append(pyproject["tool"]["poetry"])
    return pkgs


def main():
    meta = load_meta()
    pkgs = load_packages()

    is_error = False
    deps = meta["dependencies"]

    print()
    print("Current dependencies:")
    for name, version in deps.items():
        print(f"{name}: {version}")
    print()

    for pkg in pkgs:
        name = pkg["name"]
        version = pkg["version"]
        current = deps.get(name)

        if not current:
            print(f"WARN: {name} not in metapackage")
            continue

        if current != version:
            print(f"ERROR: {name} is out of date: {current} != {version}")
            is_error = True

    if is_error:
        sys.exit(1)
    else:
        print("No errors found")
        sys.exit(0)


if __name__ == "__main__":
    main()
