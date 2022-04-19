#!/usr/bin/env python3
import argparse
import json
import os
import re
import sys
from collections import defaultdict
from contextlib import contextmanager
from io import StringIO
from pathlib import Path

from pylint.lint import Run


TODO_PATTERN = re.compile(r"(todo|fixme|xxx)[\:\.]?\s*(.+)", re.IGNORECASE)


@contextmanager
def redirect():
    stdout = sys.stdout
    sys.stdout = StringIO()
    try:
        yield sys.stdout
    finally:
        sys.stdout.close()
        sys.stdout = stdout


def todo_msg(msg):
    match = TODO_PATTERN.match(msg)
    if match:
        return match.group(2)
    else:
        return msg


def main():
    parser = argparse.ArgumentParser(description="Write all todo items as rst")
    parser.add_argument("input", help="Path to source files")
    parser.add_argument("output", help="Path to output rst file")
    args = parser.parse_args()

    cmd = [
        "pylint",
        "--disable=all",
        "--enable=fixme",
        "--exit-zero",
        "-f",
        "json",
        Path(args.input).name,
    ]

    cwd = os.getcwd()
    os.chdir(Path(args.input).parent)
    try:
        with redirect() as stdout:
            Run(cmd, exit=False)
            result = json.loads(stdout.getvalue())
    finally:
        os.chdir(cwd)

    todos = defaultdict(list)
    for item in result:
        # Remove given search path from module path
        name = ".".join(item["module"].split(".")[1:])
        message = todo_msg(item["message"])
        todos[name].append({"message": todo_msg(item["message"]), "line": item["line"]})

    output = ["****", "TODO", "****", ""]
    for module, items in sorted(todos.items()):
        items.sort(key=lambda item: item["line"])

        output.append(f"{module}:")
        output.append("=" * (len(module) + 1))
        output.append("")

        output.append(".. csv-table::")
        output.append('   :header: "Line", "Message"')
        output.append("   :widths: 10, 40")
        output.append("")
        for item in items:
            output.append('   "{line}", "{message}"'.format(**item))
        output.append("")

    with open(args.output, "w") as outfile:
        outfile.write("\n".join(output))


if __name__ == "__main__":
    main()
