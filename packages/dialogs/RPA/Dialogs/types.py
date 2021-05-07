from enum import Enum
from typing import List, Dict, Union, Any

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
