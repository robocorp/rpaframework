from enum import Enum, auto
from typing import Any, Dict, List, Union

from flet import Column, Container, Row, Stack
from flet.controls.alignment import Alignment

Element = Dict[str, Any]
Options = Union[List[str], str]
Result = Dict[str, Any]


class Size(Enum):
    """Element size options"""

    Small = "small"
    Medium = "medium"
    Large = "large"


class Icon(Enum):
    """Icon variants"""

    Success = "success"
    Warning = "warning"
    Failure = "failure"


class WindowLocation(Enum):
    """A relative location for placing elements or windows"""

    Center = auto()
    TopLeft = auto()


class VerticalLocation(Enum):
    """A vertical location"""

    Left = Alignment(-1, 0)
    Center = Alignment(0, 0)
    Right = Alignment(1, 0)


class Location(Enum):
    """A relative location for placing elements or windows, that can go into any
    location
    """

    TopLeft = Alignment(-1, -1)
    TopCenter = Alignment(0, -1)
    TopRight = Alignment(1, -1)
    CenterLeft = Alignment(-1, 0)
    Center = Alignment(0, 0)
    CenterRight = Alignment(1, 0)
    BottomLeft = Alignment(-1, 1)
    BottomCenter = Alignment(0, 1)
    BottomRight = Alignment(1, 1)


SupportedFletLayout = Union[Row, Column, Container, Stack]


class PageNotOpenError(RuntimeError):
    """Raised when a method is called that requires the dialog to be open but dialog
    was not yet open"""


class LayoutError(ValueError):
    """Raised when an invalid layout is made. Debug, and do not catch these."""
