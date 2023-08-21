import traceback
from robotlibcore import HybridCore
from sphinx.application import Sphinx
from .robot import RstFormatter

IS_ROBOT_DOC = False  # Global flag for autodoc callbacks


def setup(app: Sphinx):
    app.setup_extension('sphinx.ext.autodoc')
    app.connect('autodoc-process-docstring', _process_docstring)
    app.add_config_value('libdoc_markdown', False, 'env')


def _process_docstring(app, what, name, obj, options, lines):
    if not app.config.libdoc_markdown:
        return

    if what == "class":
        if fmt := getattr(obj, "ROBOT_LIBRARY_DOC_FORMAT", "ROBOT"):
            global IS_ROBOT_DOC
            IS_ROBOT_DOC = fmt.strip().upper() == "ROBOT"

        if issubclass(obj, HybridCore):
            print(f"Detected libcore: {name}")
            _patch_libcore(obj)

    if IS_ROBOT_DOC and obj.__doc__:
        output = RstFormatter().format(obj.__doc__)
        output.replace("%TOC%", "")
        lines[:] = output.splitlines()


def _patch_libcore(klass):
    try:
        library = klass()
        for name in library.get_keyword_names():
            func = getattr(library, name)
            setattr(klass, func.__name__, func)
    except Exception:
        traceback.print_exc()
