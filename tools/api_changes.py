import subprocess
from functools import partial
import re

def main():
    run_and_capture = partial(subprocess.run, shell=True, check=True, capture_output=True, text=True)

    filename = "docs/build/html/latest.json"
    result = run_and_capture(f"git diff --unified=1 {filename}")
    regex_for_timestamp_changes = r'([-+] {8}\"generated\": \"[\d\-: ]{19}\",\n){2}'
    regex_for_linecounts = r'@@.*@@\n'
    # print(f"result.stdout: {result.stdout}")
    header_omitted = result.stdout[4:]
    diff_chunks = re.split(regex_for_linecounts, header_omitted)

    replaced = 0
    print(f"Please document following changes:")
    for chunk in diff_chunks:
        if 'object object at' in chunk or re.search(regex_for_timestamp_changes, chunk):
            replaced += 1
            continue
        if chunk:
            print(chunk)
            # without_header = result.stdout.split("\n")[5:]
    
    print(f"Omitted {replaced} irrelevant changes")
    print("After documenting the changes, git commit docs/build/html/latest.json")

if __name__ == "__main__":
    main()
