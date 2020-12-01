
from io import UnsupportedOperation
import subprocess
from functools import partial


def main():
    run_and_capture = partial(subprocess.run, shell=True, check=True, capture_output=True, text=True)
    result = run_and_capture("git status --porcelain docs/source/json/")
    change_lines = result.stdout.split("\n")
    for row in change_lines:
        if row:
            status, filename = row.split()
            if status == "D":
                print(f"Please document removal of {filename}")
            elif status == "M":
                print(f"Please document modification of {filename}")
                result = run_and_capture(f"git diff --unified=0 {filename}")
                without_header = result.stdout.split("\n")[5:]
                print(without_header)
            elif status == "A":
                print(f"Please document addition of {filename}")
                pass
            else:
                raise UnsupportedOperation(f"{filename} has invalid git status")


if __name__ == "__main__":
    main()
