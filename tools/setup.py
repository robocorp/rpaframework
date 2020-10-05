#!/usr/bin/env python3
import os
import sys

poetry_path = os.path.expanduser('~/.poetry/lib')
sys.path.append(os.path.realpath(poetry_path))

try:
	from poetry.core.masonry.builders.sdist import SdistBuilder
except ImportError:
	from poetry.masonry.builders.sdist import SdistBuilder
from poetry.factory import Factory

poetry = Factory().create_poetry(os.getcwd())
builder = SdistBuilder(poetry, None, None)

setup = builder.build_setup()
with open('setup.py', 'wb') as fd:
    fd.write(setup)
