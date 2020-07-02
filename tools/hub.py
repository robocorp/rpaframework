#!/usr/bin/env python3
import argparse
import re
import subprocess
from pathlib import Path

FRONTMATTER = """\
---
title: '{title}'
date: '{date}'
---
"""


def file_timestamp(path):
    output = subprocess.check_output(
        ["git", "log", "-1", "--date=iso-strict", "--pretty=%cI", path]
    )
    return output.decode().strip()


def convert_file(args, path):
    # Read converted markdown
    with open(path) as fd:
        content = fd.readlines()

    # Prepend 'RPA.' to library name if missing
    for index, line in enumerate(content):
        if line.strip():
            match = re.match(r"^#\s+(.+)", line)
            assert match
            name = match.group(1).strip()
            assert name

            if not name.startswith("RPA"):
                name = f"RPA.{name}"

            content = [f"# {name}\n"] + content[index + 1 :]
            break

    # Create frontmatter
    source = Path(args.source, Path(path).relative_to(args.build)).with_suffix(".rst")
    frontmatter = FRONTMATTER.format(title=name, date=file_timestamp(source))

    # Write docs with frontmatter to dist folder
    path = Path(args.dist, path.parent.name).with_suffix(".md")
    with open(path, "w") as fd:
        fd.write(frontmatter)
        fd.writelines(content)


def main():
    parser = argparse.ArgumentParser(
        description="Convert markdown files to be Robohub-compatible"
    )
    parser.add_argument("source")
    parser.add_argument("build")
    parser.add_argument("dist")

    args = parser.parse_args()

    assert Path(args.source).is_dir()
    assert Path(args.build).is_dir()
    assert Path(args.dist).is_dir()

    for path in Path(args.build).rglob("index.md"):
        convert_file(args, path)


if __name__ == "__main__":
    main()
