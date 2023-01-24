from enum import Enum, auto
from typing import Any, Dict, List, Union


Element = Dict[str, Any]
Elements = List[Element]
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


class Location(Enum):
    Center = auto()
    BottomLeft = auto()
    TopLeft = auto()
    BottomRight = auto()
    TopRight = auto()
