#!/usr/bin/env python3
import argparse
import json
import os
from pathlib import Path

FILENAME = "latest.json"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("dirname", help="Path to directory of JSONS")
    args = parser.parse_args()

    dirname = Path(args.dirname)

    output = {}
    for filename in sorted(os.listdir(dirname)):
        if filename == FILENAME:
            continue
        with open(dirname / filename, "r") as infile:
            lib = json.load(infile)
            assert lib["name"] not in output, "Duplicate library"
            output[lib["name"]] = lib

    with open(dirname / FILENAME, "w") as outfile:
        json.dump(output, outfile, indent=4)


if __name__ == "__main__":
    main()
