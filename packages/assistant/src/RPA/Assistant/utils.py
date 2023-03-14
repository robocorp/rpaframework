from typing import Any, Dict, List, Optional, Tuple, Union

from typing_extensions import Literal
from RPA.core.types import is_list_like  # type: ignore

from RPA.Assistant.types import Element, Location, Options


def to_options(
    opts: Options, default: Optional[str] = None
) -> Tuple[List[str], Optional[str]]:
    """Convert keyword argument for multiple options into
    a list of strings.

    Also handles default option validation.
    """
    if isinstance(opts, str):
        opts = [opt.strip() for opt in opts.split(",")]
    elif is_list_like(opts):
        opts = [str(opt) for opt in opts]
    else:
        raise ValueError(f"Unsupported options type: {opts}")

    if not opts:
        return [], None

    if default is None:
        default = opts[0]

    if default not in opts:
        raise ValueError(f"Default '{default}' is not in available options")

    return opts, default


def optional_str(val: Any) -> Optional[str]:
    """Convert value to string, but keep NoneType"""
    return str(val) if val is not None else val


def optional_int(val: Any) -> Optional[int]:
    """Convert value to int, but keep NoneType"""
    return int(val) if val is not None else val


def int_or_auto(val: Any) -> Union[int, str]:
    """Convert value to int or 'AUTO' literal"""
    if isinstance(val, int):
        return val

    try:
        return int(val)
    except ValueError:
        pass

    height = str(val).strip().upper()
    if height == "AUTO":
        return height

    raise ValueError("Value not integer or AUTO")


def is_input(element: Element) -> bool:
    """Check if an element is an input"""
    return element["type"].startswith("input-")


def is_submit(element: Element) -> bool:
    """Check if an element is a submit button."""
    return element["type"] == "submit"


def location_to_absolute(
    location: Union[Location, Tuple[int, int], None],
    parent_width: float,
    parent_height: float,
    element_width: Optional[float],
    element_height: Optional[float],
) -> Dict[Literal["left", "top", "bottom", "right"], float]:
    """Calculates and returns absolute version of elements relative position as left or
    right and bottom or top keys in dictionary.
    """
    if isinstance(location, tuple):
        return {"left": location[0], "top": location[1]}

    if location in [
        Location.TopCenter,
        Location.BottomCenter,
        Location.CenterLeft,
        Location.CenterRight,
        Location.Center,
    ]:
        if element_height is None or element_width is None:
            raise ValueError(
                "Cannot determine centered position without static width and height"
            )
        half_height = (parent_height / 2) - (element_height / 2)
        half_width = (parent_width / 2) - (element_width / 2)
    else:
        half_height, half_width = -1, -1

    coordinates: Dict[
        Location, Dict[Literal["left", "top", "bottom", "right"], float]
    ] = {
        Location.TopLeft: {"left": 0, "top": 0},
        Location.TopCenter: {"left": half_width, "top": 0},
        Location.TopRight: {"right": 0, "top": 0},
        Location.CenterLeft: {"left": 0, "top": half_height},
        Location.Center: {"left": half_width, "top": half_height},
        Location.CenterRight: {"right": 0, "top": half_width},
        Location.BottomLeft: {"left": 0, "bottom": 0},
        Location.BottomCenter: {"left": half_width, "bottom": 0},
        Location.BottomRight: {"right": 0, "bottom": 0},
    }

    if isinstance(location, Location):
        return coordinates[location]
    else:
        raise ValueError(f"Invalid location {location}")
