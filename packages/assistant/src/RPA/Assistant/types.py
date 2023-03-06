from enum import Enum, auto
from typing import Any, Dict, List, Union

from flet_core import alignment

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

    Left = alignment.center_left
    Center = alignment.center
    Right = alignment.center_right


class Location(Enum):
    """A relative location for placing elements or windows, that can go into any
    location
    """

    TopLeft = alignment.top_left
    TopCenter = alignment.top_center
    TopRight = alignment.top_right
    CenterLeft = alignment.center_left
    Center = alignment.center
    CenterRight = alignment.center_right
    BottomLeft = alignment.bottom_left
    BottomCenter = alignment.bottom_center
    BottomRight = alignment.bottom_right
