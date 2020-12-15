from dataclasses import dataclass, astuple
from typing import Any, Optional, Union, Sequence, Tuple


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
class Undefined:
    """Internal placeholder for generic geometry."""

    def __str__(self):
        return "undefined"


@dataclass(order=True)
class Point:
    """Container for a 2D point."""

    x: int
    y: int

    def __post_init__(self):
        self.x = int(self.x)
        self.y = int(self.y)

    def __str__(self):
        return f"point:{self.x},{self.y}"

    def __iter__(self):
        return iter(self.as_tuple())

    def as_tuple(self) -> Tuple:
        return astuple(self)

    def move(self, x: int, y: int) -> "Point":
        """Move the point relativce to the current position,
        and return the resulting copy.
        """
        return Point(self.x + int(x), self.y + int(y))


@dataclass(order=True)
class Region:
    """Container for a 2D rectangular region."""

    left: int
    top: int
    right: int
    bottom: int

    def __post_init__(self):
        self.left = int(self.left)
        self.top = int(self.top)
        self.right = int(self.right)
        self.bottom = int(self.bottom)

        if self.left >= self.right:
            raise ValueError("Invalid width")
        if self.top >= self.bottom:
            raise ValueError("Invalid height")

    def __str__(self):
        return f"region:{self.left},{self.top},{self.right},{self.bottom}"

    def __iter__(self):
        return iter(self.as_tuple())

    @classmethod
    def from_size(cls, left: int, top: int, width: int, height: int) -> "Region":
        return cls(left, top, left + width, top + height)

    @classmethod
    def merge(cls, regions: Sequence["Region"]) -> "Region":
        left = min(region.left for region in regions)
        top = min(region.top for region in regions)
        right = max(region.right for region in regions)
        bottom = max(region.bottom for region in regions)

        return cls(left, top, right, bottom)

    @property
    def width(self) -> int:
        return self.right - self.left

    @width.setter
    def width(self, value: int):
        diff = int(value) - self.width
        if self.width + diff <= 0:
            raise ValueError("Invalid width")

        self.left -= int(diff / 2)
        self.right += int(diff / 2)

    @property
    def height(self) -> int:
        return self.bottom - self.top

    @height.setter
    def height(self, value: int):
        diff = int(value) - self.height
        if self.height + diff <= 0:
            raise ValueError("Invalid height")

        self.top -= int(diff / 2)
        self.bottom += int(diff / 2)

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
        """Scale all coordinate values with a given factor.

        Used for instance when regions are from a monitor with
        different pixel scaling.
        """
        left = int(self.left * scaling_factor)
        top = int(self.top * scaling_factor)
        right = int(self.right * scaling_factor)
        bottom = int(self.bottom * scaling_factor)

        return Region(left, top, right, bottom)

    def resize(self, *sizes: int) -> "Region":
        """Grow or shrink the region a given amount of pixels,
        and return the resulting copy.

        The method supports different ways to resize:

        resize(a):          a = all edges
        resize(a, b):       a = left/right, b = top/bottom
        resize(a, b, c):    a = left, b = top/bottom, c = right
        resize(a, b, c, d): a = left, b = top, c = right, d = bottom
        """
        count = len(sizes)
        if count == 1:
            left = top = right = bottom = sizes[0]
        elif count == 2:
            left = right = sizes[0]
            top = bottom = sizes[1]
        elif count == 3:
            left = sizes[0]
            top = bottom = sizes[1]
            right = sizes[2]
        elif count == 4:
            left, top, right, bottom = sizes
        else:
            raise ValueError(f"Too many resize arguments: {count}")

        left = self.left - int(left)
        top = self.top - int(top)
        right = self.right + int(right)
        bottom = self.bottom + int(bottom)

        return Region(left, top, right, bottom)

    def move(self, left: int, top: int) -> "Region":
        """Move the region relative to current position,
        and return the resulting copy.
        """
        left = self.left + int(left)
        top = self.top + int(top)
        right = left + self.width
        bottom = top + self.height

        return Region(left, top, right, bottom)

    def contains(self, element: Union[Point, "Region"]) -> bool:
        """Check if a point or region is inside this region."""
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

    def clamp(self, container: "Region") -> "Region":
        """Limit the region to the maximum dimensions defined by the container,
        and return the resulting copy.
        """
        left = max(container.left, min(self.left, container.right))
        top = max(container.top, min(self.top, container.bottom))
        right = min(container.right, max(self.right, container.left))
        bottom = min(container.bottom, max(self.bottom, container.top))

        return Region(left, top, right, bottom)
