#!/usr/bin/env python

#  Copyright 2008-2015 Nokia Networks
#  Copyright 2016-     Robot Framework Foundation
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

# NOTE(cmin764; 7 Sep 2023): Vendorizing `robotframework`'s entry-point in order to
#  execute the SSL injection (and ony other runtime patch) as soon as possible, way
#  before importing any other package, thus risking failing the injection.
# pylint: disable=unused-import
import RPA.core  # noqa: F401

import sys

if __name__ == "__main__" and "robot" not in sys.modules:
    # pylint: disable=unused-import
    import pythonpathsetter  # noqa: F401

from robot import run_cli

run_cli()
