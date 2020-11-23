from dataclasses import dataclass, astuple
from typing import Any, Optional, Union, List, Tuple


def to_point(obj: Any) -> Optional["Point"]:
    """Convert `obj` to instance of Point."""
    if obj is None or isinstance(obj, Point):
        return obj
    if isinstance(obj, str):
        obj = obj.split(",")
    return Point(*(int(i) for i in obj))


def to_region(obj: Any) -> Optional["Region"]:
    """Convert `obj` to instance of Region."""
    if obj is None or isinstance(obj, Region):
        return obj
    if isinstance(obj, str):
        obj = obj.split(",")
    return Region(*(int(i) for i in obj))


@dataclass
class Point:
    """Container for a 2D point."""

    x: int
    y: int

    def __iter__(self):
        return iter(self.as_tuple())

    def as_tuple(self) -> Tuple:
        return astuple(self)

    def move(self, x: int, y: int) -> "Point":
        return Point(self.x + int(x), self.y + int(y))


@dataclass
class Region:
    """Container for a 2D rectangular region."""

    left: int
    top: int
    right: int
    bottom: int

    def __post_init__(self):
        if self.left >= self.right:
            raise ValueError("Invalid width")
        if self.top >= self.bottom:
            raise ValueError("Invalid height")

    def __iter__(self):
        return iter(self.as_tuple())

    @classmethod
    def from_size(cls, left: int, top: int, width: int, height: int) -> "Region":
        return cls(left, top, left + width, top + height)

    @classmethod
    def merge(cls, regions: List["Region"]) -> "Region":
        left = min(region.left for region in regions)
        top = min(region.top for region in regions)
        right = max(region.right for region in regions)
        bottom = max(region.bottom for region in regions)

        return cls(left, top, right, bottom)

    @property
    def width(self) -> int:
        return self.right - self.left

    @property
    def height(self) -> int:
        return self.bottom - self.top

    @property
    def area(self) -> int:
        return self.width * self.height

    @property
    def center(self) -> Point:
        return Point(
            x=int((self.left + self.right) / 2), y=int((self.top + self.bottom) / 2)
        )

    def as_tuple(self) -> Tuple:
        return astuple(self)

    def scale(self, scaling_factor: float) -> "Region":
        left = int(self.left * scaling_factor)
        top = int(self.top * scaling_factor)
        right = int(self.right * scaling_factor)
        bottom = int(self.bottom * scaling_factor)

        return Region(left, top, right, bottom)

    def move(self, left: int, top: int) -> "Region":
        left = self.left + int(left)
        top = self.top + int(top)
        right = left + self.width
        bottom = top + self.height

        return Region(left, top, right, bottom)

    def contains(self, element: Union[Point, "Region"]) -> bool:
        if isinstance(element, Point):
            return (self.left <= element.x <= self.right) and (
                self.top <= element.y <= self.bottom
            )
        elif isinstance(element, Region):
            return (
                element.left >= self.left
                and element.top >= self.top
                and element.right <= self.right
                and element.bottom <= self.bottom
            )
        else:
            raise NotImplementedError("contains() only supports Points and Regions")
