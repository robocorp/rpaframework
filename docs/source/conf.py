# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
# import os
# import sys
# sys.path.insert(0, os.path.abspath('../../src/rpa'))

# -- Project information -----------------------------------------------------

project = "RPA Framework"
copyright = "2020 Robocorp Technologies, Inc."
author = "Ossi Rajuvaara, Mika Hänninen"

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.todo",
    "sphinx_markdown_builder",
    "sphinx_issues",
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []

# Render todo and todolist directives
todo_include_todos = True

# Github project for issue / pr directives
issues_github_path = "robocorp/rpaframework"

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "sphinx_rtd_theme"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]
html_extra_path = ["include"]
html_css_files = ["custom.css"]
html_js_files = ["iframeResizer.min.js", "custom.js"]

# -- Override Robot Framework lexer ------------------------------------------
from robotframeworklexer import RobotFrameworkLexer
from sphinx.highlighting import lexers

lexers["robotframework"] = RobotFrameworkLexer()
