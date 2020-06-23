#!/usr/bin/env python3
"""
Create test data for FilesLibrary acceptance tests
"""
import argparse
import os
from pathlib import Path


def touch(path):
    Path(path).touch()


def mkdir(path):
    os.makedirs(path)


def write(path, content):
    if isinstance(content, str):
        content = content.encode("utf-8")
    with open(path, "wb") as fd:
        fd.write(content)


def prepare():
    mkdir("subfolder/first")
    mkdir("subfolder/second")
    mkdir("another/first")
    mkdir("another/second")
    mkdir("empty")

    touch("emptyfile")
    touch("notemptyfile")
    touch("sorted1.test")
    touch("sorted2.test")
    touch("sorted3.test")
    touch("subfolder/first/stuff.ext")
    touch("subfolder/second/stuff.ext")
    touch("another/first/noext")
    touch("another/second/one")
    touch("another/second/two")
    touch("another/second/three")
    touch("another/second/.dotfile")

    write("notemptyfile", "some content here")
    write("somebytes", b"\x00\x66\x6f\x6f\x00")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "root", default=os.getcwd(), help="Root directory for mock files"
    )
    args = parser.parse_args()

    mkdir(args.root)
    os.chdir(args.root)

    prepare()
