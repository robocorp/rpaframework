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


class HorizontalLocation(Enum):
    """A horizontal location"""

    Left = Alignment.CENTER_LEFT
    Center = Alignment.CENTER
    Right = Alignment.CENTER_RIGHT


class Location(Enum):
    """A relative location for placing elements or windows, that can go into any
    location
    """

    TopLeft = auto()
    TopCenter = auto()
    TopRight = auto()
    CenterLeft = auto()
    Center = auto()
    CenterRight = auto()
    BottomLeft = auto()
    BottomCenter = auto()
    BottomRight = auto()


SupportedFletLayout = Union[Row, Column, Container, Stack]


class PageNotOpenError(RuntimeError):
    """Raised when a method is called that requires the dialog to be open but dialog
    was not yet open"""


class LayoutError(ValueError):
    """Raised when an invalid layout is made. Debug, and do not catch these."""
