#!/usr/bin/env python3
import datetime
from html import escape
import re
from pathlib import Path
import subprocess

PATTERN_VERSION = re.compile(r"^([0-9]+)\.([0-9]+)\.([0-9]+)")
PATTERN_CONTEXT = re.compile(r"- (\S+):")
PATTERN_BOLD_TEXT = re.compile(r".*\*(.*)\*.*")
PATTERN_GIT_TAG = re.compile(
    r"(.*)\(.*tag: main_([0-9]{1,2}\.[0-9]{1,2}\.[0-9]{1,2}).*\)"
)

RELEASENOTES = Path(
    Path(__file__).resolve().parent, "..", "docs", "source", "releasenotes.rst"
)

RSSFEED = Path(
    Path(__file__).resolve().parent, "..", "docs", "build", "html", "releases.xml"
)


def run(*args):
    return subprocess.check_output(*args, stderr=subprocess.STDOUT).decode().strip()


def get_git_tags():
    command = [
        "git",
        "log",
        "--tags",
        "--simplify-by-decoration",
        "--pretty=%ai %d",
    ]
    result = run(command)
    matches = PATTERN_GIT_TAG.findall(result)
    git_releases = {}
    for m in matches:
        reldate = datetime.datetime.strptime(
            m[0].strip(),
            "%Y-%m-%d %H:%M:%S %z",
        ).strftime("%a, %d %b %Y %H:%M:%S %z")
        git_releases[m[1]] = reldate
    return git_releases


def to_markup(line):
    line = line.replace("``", "`")
    line = line.replace("**", "*")
    line = line.replace("(*", "*")
    line = line.replace("*)", "*")
    line = line.replace("<", "")
    line = line.replace(">", "")

    matches = PATTERN_CONTEXT.match(line)
    if matches:
        context = matches.group(1)
        if "*" not in context:
            line = line.replace(context, f"<b>{context}</b>", 1)
    matches = PATTERN_BOLD_TEXT.match(line)
    if matches:
        context = matches.group(1)
        line = line.replace("*", "")
        line = line.replace(context, f"<b>{context}</b>", 1)
    line = f"{line}<br>"
    return escape(line)


def rss_header():
    return """
<rss version="2.0">
\t<channel>
\t<title>Recent updates for rpaframework</title>
\t<link>https://rpaframework.org/releasenotes.html</link>
\t<description>Recent updates to the Python Package Index for rpaframework</description>
\t<language>en</language>"""


def rss_footer():
    return """\t</channel>
</rss>
"""


def rss_item(title, desc, pubdate):
    return f"""
\t<item>
\t\t<title>Release {title}</title>
\t\t<link>https://pypi.org/project/rpaframework/{title}/</link>
\t\t<description>{desc}</description>
\t\t<author>rpafw@robocorp.com</author>
\t\t<pubDate>{pubdate}</pubDate>
\t\t<source url="https://rpaframework.org/releasenotes.html">Release Notes</source>
\t</item>"""


def main():
    releases = []
    with open(RELEASENOTES) as fd:
        version = None

        output = []
        for line in fd:
            if PATTERN_VERSION.match(line):
                if version and len(output) > 0:
                    releases.append({"version": version, "output": output})
                output = []
                version = line.strip()
                next(fd)  # Skip header formatting
            else:
                if line.strip():
                    output.append(to_markup(line))

    git_releases = get_git_tags()
    rss_content = rss_header()

    for rel in releases:
        version = rel["version"]
        description = "    ".join(rel["output"])
        if version in git_releases.keys():
            rss_content += rss_item(version, description, git_releases[version])
    rss_content += rss_footer()
    with open(RSSFEED, "w") as fout:
        fout.write(rss_content)


if __name__ == "__main__":
    main()
