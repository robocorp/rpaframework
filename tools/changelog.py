#!/usr/bin/env python3
import re
from pathlib import Path

PATTERN_VERSION = re.compile(r"^([0-9]+)\.([0-9]+)\.([0-9]+)")
PATTERN_CONTEXT = re.compile(r"- (\S+):")

RELEASENOTES = Path(
    Path(__file__).resolve().parent, "..", "docs", "source", "releasenotes.rst"
)


def to_markup(line):
    line = line.replace("``", "`")
    line = line.replace("**", "*")

    matches = PATTERN_CONTEXT.match(line)
    if matches:
        context = matches.group(1)
        if "*" not in context:
            line = line.replace(context, f"*{context}*", 1)

    return line


def main():
    with open(RELEASENOTES) as fd:
        version = None
        for line in fd:
            if PATTERN_VERSION.match(line):
                version = line.strip()
                next(fd)  # Skip header formatting
                break

        assert version

        output = []
        for line in fd:
            if PATTERN_VERSION.match(line):
                break
            if line.strip():
                output.append(to_markup(line))

        print(f"\nrpa-framework version *{version}*\n")
        print("".join(output))


if __name__ == "__main__":
    main()
