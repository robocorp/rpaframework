#!/usr/bin/env python3
"""
Robot Framework Libdoc Extended Edition
"""
import abc
import argparse
import json
import logging
import os
import re
import sys
from contextlib import contextmanager
from pathlib import Path

from robot.errors import DataError
from robot.libdocpkg import LibraryDocumentation, htmlwriter
from robot.utils import normalize, unic

BLACKLIST = ("__pycache__",)
INIT_FILES = ("__init__.robot", "__init__.txt")
EXTENSIONS = (".robot", ".resource", ".txt")
CONVERTERS = {}  # Populated dynamically


class ConverterMeta(abc.ABCMeta):
    def __new__(cls, name, bases, dct):
        converter = super().__new__(cls, name, bases, dct)
        if name == "BaseConverter":
            return converter

        if not getattr(converter, "NAME", None):
            raise ValueError(f"Undefined 'NAME' attribute in {converter}")
        if not getattr(converter, "EXTENSION", None):
            raise ValueError(f"Undefined 'EXTENSION' attribute in {converter}")
        if converter.NAME in CONVERTERS:
            raise ValueError(f"Duplicate converter for {converter.NAME}")

        CONVERTERS[converter.NAME] = converter
        return converter


class BaseConverter(metaclass=ConverterMeta):
    NAME = None
    EXTENSION = None

    @abc.abstractmethod
    def convert(self, libdoc, output):
        raise NotImplementedError


class JsonConverter(BaseConverter):
    NAME = "json"
    EXTENSION = ".json"

    class _NullFormatter:
        def html(self, doc, *args, **kwargs):
            return doc

    def convert(self, libdoc, output):
        data = htmlwriter.JsonConverter(self._NullFormatter()).convert(libdoc)
        with open(output, "w") as fd:
            json.dump(data, fd, indent=4)


class JsonHtmlConverter(BaseConverter):
    NAME = "json-html"
    EXTENSION = ".json"

    def convert(self, libdoc, output):
        formatter = htmlwriter.DocFormatter(
            libdoc.keywords, libdoc.doc, libdoc.doc_format
        )
        data = htmlwriter.JsonConverter(formatter).convert(libdoc)
        with open(output, "w") as fd:
            json.dump(data, fd, indent=4)


class XmlConverter(BaseConverter):
    NAME = "xml"
    EXTENSION = ".xml"

    def convert(self, libdoc, output):
        libdoc.save(output, "XML")


class HtmlConverter(BaseConverter):
    NAME = "html"
    EXTENSION = ".html"

    def convert(self, libdoc, output):
        libdoc.save(output, "HTML")


class XmlHtmlConverter(BaseConverter):
    NAME = "xml-html"
    EXTENSION = ".html"

    def convert(self, libdoc, output):
        libdoc.save(output, "XML:HTML")


class RestConverter(BaseConverter):
    NAME = "rest"
    EXTENSION = ".rst"

    IGNORE = (r"^:param.*", r"^:return.*")

    def __init__(self):
        self.ignore_block = False

    def convert(self, libdoc, output):
        writer = RestWriter()
        with writer.heading(libdoc.name):
            self.overview(writer, libdoc)
            # self.inits(writer, libdoc)
            self.keywords(writer, libdoc)

        with open(output, "w") as fd:
            fd.write(writer.as_text())

    def filter_docstring(self, text):
        output = []
        for line in text.split("\n"):
            if any(re.match(pattern, line) for pattern in self.IGNORE):
                self.ignore_block = True
                continue
            elif line.startswith(" ") and self.ignore_block:
                continue

            self.ignore_block = False
            output.append(line)
        return "\n".join(output)

    @staticmethod
    def escape_string(text):
        return text.replace("*", "\\*")

    def overview(self, writer, libdoc):
        with writer.heading("Description"):
            writer.fieldlist(("Library scope", libdoc.scope))
            writer.raw(self.filter_docstring(libdoc.doc))

    def inits(self, writer, libdoc):
        with writer.heading("Init"):
            for init in libdoc.inits:
                writer.raw(init.doc)

    def keywords(self, writer, libdoc):
        with writer.heading("Keywords"):
            for kw in libdoc.keywords:
                with writer.field(kw.name):
                    fields = []
                    if kw.args:
                        args = (self.escape_string(arg) for arg in kw.args)
                        fields.append(("Arguments", ", ".join(args)))
                    if kw.tags:
                        fields.append(("Tags", ", ".join(kw.tags)))
                    writer.fieldlist(*fields)
                    writer.raw(self.filter_docstring(kw.doc))


class RestHtmlConverter(RestConverter):
    NAME = "rest-html"
    EXTENSION = ".rst"

    def convert(self, libdoc, output):
        formatter = htmlwriter.DocFormatter(
            libdoc.keywords, libdoc.doc, libdoc.doc_format
        )

        libdoc.doc = self._raw_html(formatter.html(libdoc.doc))
        for init in libdoc.inits:
            init.doc = self._raw_html(formatter.html(init.doc))
        for kw in libdoc.keywords:
            kw.doc = self._raw_html(formatter.html(kw.doc))

        super().convert(libdoc, output)

    def _raw_html(self, content):
        output = [".. raw:: html", ""]
        for line in content.splitlines():
            output.append(f"   {line}")
        return "\n".join(output)


class RestWriter:
    """Helper class for writing reStructuredText"""

    INDENT = "  "

    def __init__(self):
        self.body = []
        self._indent = 0
        self._section = 0

    def write(self, text=""):
        for line in text.split("\n"):
            # Do not indent empty lines
            if not line.strip():
                self.body.append("")
                continue

            self.body.append(
                "{indent}{line}".format(indent=self.INDENT * self._indent, line=line)
            )

    def as_text(self):
        return "\n".join(self.body)

    def raw(self, text):
        self.write(text)
        self.write()

    @contextmanager
    def heading(self, content):
        try:
            self._heading(content)
            self._section += 1
            yield
        finally:
            self._section -= 1

    def _heading(self, content):
        chars = "#*=-"
        line = chars[self._section] * len(content)

        if self._section < 2:
            self.write(line)
        self.write(content)
        self.write(line)
        self.write()

    @contextmanager
    def field(self, name):
        try:
            self.write(f":{name}:")
            self._indent += 1
            yield
        finally:
            self._indent -= 1

    def fieldlist(self, *values):
        if not values:
            return
        for name, value in values:
            self.write(f":{name}: {value}")
        self.write()


class LibdocExt:
    DOC_FORMATS = ("robot", "text", "html", "rest")

    def __init__(self, config=None):
        self.logger = logging.getLogger(__name__)
        self.config = config or {}

    def convert_all(self, dir_in, dir_out, format_in, format_out):
        self.logger.info(
            "Searching for libraries in '%s'", ", ".join(str(d) for d in dir_in)
        )
        paths = self.find_keyword_files(dir_in)
        assert paths, "No keyword files found"

        dir_out = Path(dir_out)
        parent = os.path.dirname(os.path.commonprefix(paths))

        converter = CONVERTERS[format_out]
        errors = set()
        for path_in in paths:
            path_rel = path_in.with_suffix(converter.EXTENSION).relative_to(parent)
            path_out = dir_out / path_rel
            path_out.parent.mkdir(parents=True, exist_ok=True)

            try:
                self.logger.info("Converting '%s' to '%s'", path_in, path_out)
                libdoc = self.parse_documentation(path_in, format_in, path_rel.parent)
                converter().convert(libdoc, path_out)
            except Exception as err:
                self.logger.error(str(err).split("\n")[0])
                errors.add(path_in)

        return list(errors)

    def find_keyword_files(self, root):
        paths, stack = set(), [Path(r) for r in root]

        while stack:
            path = stack.pop(0)
            if self.should_ignore(path):
                self.logger.debug("Ignoring file: %s", path)
                continue
            elif path.is_dir():
                if self.is_module_library(path):
                    paths.add(path)
                    # Check for RF resources files in module
                    paths |= {
                        file
                        for file in path.glob("**/*")
                        if self.is_resource_file(path)
                    }
                else:
                    for child in path.iterdir():
                        stack.append(child)
            elif self.is_keyword_file(path):
                paths.add(path)

        return list(paths)

    def should_ignore(self, path):
        return path in self.config.get("ignore", []) or path.name in BLACKLIST

    def parse_documentation(self, path, doc_format, namespace=None):
        libdoc = LibraryDocumentation(str(path), doc_format=doc_format.upper())

        # Override name with user-given value
        if self.config.get("title"):
            libdoc.name = self.config["title"]
        # Create module path for library, e.g. RPA.Excel.Files
        elif namespace not in (None, Path(".")):
            libdoc.name = "{namespace}.{name}".format(
                namespace=str(namespace).replace(os.sep, "."), name=libdoc.name,
            )

        # Convert scope to RPA format
        if self.config.get("rpa", False):
            scope = normalize(unic(libdoc.scope), ignore="_")
            libdoc.scope = {
                "testcase": "Task",
                "testsuite": "Suite",
                "global": "Global",
            }.get(scope, "")

        return libdoc

    @staticmethod
    def is_module_library(path):
        return (path / "__init__.py").is_file() and bool(
            LibraryDocumentation(str(path)).keywords
        )

    @staticmethod
    def is_keyword_file(file):
        return LibdocExt.is_library_file(file) or LibdocExt.is_resource_file(file)

    @staticmethod
    def is_library_file(file):
        return file.suffix == ".py" and file.name != "__init__.py"

    @staticmethod
    def is_resource_file(file):
        if file.name in INIT_FILES or file.suffix not in EXTENSIONS:
            return False

        def contains(data, pattern):
            return bool(re.search(pattern, data, re.MULTILINE | re.IGNORECASE))

        with open(file, "r", encoding="utf-8", errors="ignore") as fd:
            data = fd.read()
            has_keywords = contains(data, r"^\*+\s*((?:User )?Keywords?)")
            has_tasks = contains(data, r"^\*+\s*(Test Cases?|Tasks?)")
            return not has_tasks and has_keywords


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("path", help="Input file path", type=Path, nargs="+")
    parser.add_argument("-t", "--title", help="Override title for generated files")
    parser.add_argument(
        "-o",
        "--output",
        help="Output directory",
        type=Path,
        default=Path("dist", "libdoc"),
    )
    parser.add_argument(
        "-f", "--format", help="Output format", choices=CONVERTERS, default="json"
    )
    parser.add_argument(
        "-d",
        "--docstring",
        help="Input docstring format",
        choices=LibdocExt.DOC_FORMATS,
        default="robot",
    )
    parser.add_argument(
        "-i",
        "--ignore",
        action="append",
        default=[],
        type=Path,
        help="Ignore given path",
    )
    parser.add_argument("--rpa", action="store_true", help="Use tasks instead of tests")
    parser.add_argument(
        "--ignore-errors", action="store_true", help="Ignore all conversion errors"
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Be more talkative"
    )
    args = parser.parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        stream=sys.stdout,
        level=log_level,
        format="%(asctime)s %(levelname)-8s %(message)s",
    )

    app = LibdocExt(
        config={"title": args.title, "ignore": args.ignore, "rpa": args.rpa}
    )

    try:
        errors = app.convert_all(
            dir_in=args.path,
            dir_out=args.output,
            format_in=args.docstring,
            format_out=args.format,
        )
    except DataError as err:
        logging.error("Failed to parse library: %s", err)
        sys.exit(1)

    if errors and not args.ignore_errors:
        logging.error(
            "Failed to convert the following libraries:\n%s",
            "\n".join(f"{i}. {path}" for i, path in enumerate(sorted(errors), 1)),
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
