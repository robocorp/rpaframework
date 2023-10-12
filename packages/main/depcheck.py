import re
import subprocess
from collections import defaultdict
from packaging import version as version_parser

def to_version(ver):
    return version_parser.parse(ver)


def main():
    tree = subprocess.check_output(["poetry", "show", "--tree", "--only", "main"], text=True)

    packages = defaultdict(set)
    for line in tree.splitlines():
        line = line.strip("└│├── ")
        line = line.rstrip("(circular dependency aborted here)")
        parts = line.split(" ")

        name = parts[0]
        for part in parts[1:]:
            if re.match("^[A-Za-z]", part):
                break
            for const in part.split(","):
                packages[name].add(const)

    floating = []
    unbounded = []

    for name, constraints in packages.items():
        min_version = None
        min_inclusive = False
        max_version = None
        max_inclusive = False

        for const in constraints:
            if const.startswith(">="):
                version = to_version(const[2:])
                if min_version is None or version > min_version:
                    min_version = version
                    min_inclusive = True
            elif const.startswith(">"):
                version = to_version(const[1:])
                if min_version is None or version > min_version or (version == min_version and min_inclusive):
                    min_version = version
                    min_inclusive = False
            elif const.startswith("<="):
                version = to_version(const[2:])
                if max_version is None or version < max_version:
                    max_version = version
                    max_inclusive = True
            elif const.startswith("<"):
                version = to_version(const[1:])
                if max_version is None or version < max_version or (version == max_version and max_inclusive):
                    max_version = version
                    max_inclusive = False
            elif const == "*":
                pass
            elif const == "||":
                # TODO: Handling this requires refactoring
                pass
            else:
                try:
                    version = to_version(const)
                    max_version = min_version = version
                    max_inclusive = min_inclusive = True
                    break
                except Exception:
                    raise NotImplementedError(f"Unhandled constraint: {const}")

        if min_version is None and max_version is None:
            floating.append(name)
        elif max_version is None:
            unbounded.append(name)

    for name in sorted(floating):
        print(f"Floating version: {name}")
    print()
    for name in sorted(unbounded):
        print(f"No upper bound: {name}")


if __name__ == "__main__":
    main()
