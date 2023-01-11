"""This module extends ``include`` to allow globbing."""
import os

from docutils.parsers.rst.directives.misc import Include
from docutils.parsers.rst import directives

from pathlib import Path
from glob import glob

from sphinx.locale import _
from sphinx.util.docutils import SphinxDirective


class IncludeGlob(Include):

    required_arguments = 0
    has_content = True

    def run(self):
        # Pseudocode for this method:
        #  for path in glob(paths):
        #    Include.run(self)

        # get argument
        nodes = []
        for arg in self.content:
            if arg[0] == os.pathsep:
                paths = sorted(glob(arg, recursive=True))
            else:
                source = self.state_machine.input_lines.source(
                    self.lineno - self.state_machine.input_offset - 1
                )
                source_dir = os.path.dirname(os.path.abspath(source))
                paths = sorted(glob(str(Path(source_dir) / arg)))
            print(f"Paths to be included via glob: {paths}")
            for path in paths:
                self.arguments.insert(0, path)
                print(f"running include on {path}")
                nodes.extend(super().run())

        return nodes


def setup(app):
    app.add_directive("includeglob", IncludeGlob)

    return {
        "version": "0.1",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
