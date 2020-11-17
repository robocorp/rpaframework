from dataclasses import dataclass, astuple
from typing import Union


def to_point(obj):
    """Convert `obj` to instance of Point."""
    if obj is None or isinstance(obj, Point):
        return obj
    if isinstance(obj, str):
        obj = obj.split(",")
    return Point(*(int(i) for i in obj))


def to_region(obj):
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

    def as_tuple(self):
        return astuple(self)

    def offset(self, x, y):
        self.x += int(x)
        self.y += int(y)


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
    def from_size(cls, left, top, width, height):
        return cls(left, top, left + width, top + height)

    @property
    def width(self):
        return self.right - self.left

    @property
    def height(self):
        return self.bottom - self.top

    @property
    def area(self):
        return self.width * self.height

    @property
    def center(self):
        return Point(
            x=int((self.left + self.right) / 2), y=int((self.top + self.bottom) / 2)
        )

    def as_tuple(self):
        return astuple(self)

    def scale(self, scaling_factor: float):
        self.left = int(self.left * scaling_factor)
        self.top = int(self.top * scaling_factor)
        self.right = int(self.right * scaling_factor)
        self.bottom = int(self.bottom * scaling_factor)

    def move(self, left, top):
        width, height = self.width, self.height
        self.left = self.left + int(left)
        self.top = self.top + int(top)
        self.right = self.left + width
        self.bottom = self.top + height

    def contains(self, element: Union[Point, "Region"]):
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
            raise NotImplementedError("Contains only supports Points and Regions")
