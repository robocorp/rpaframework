from abc import ABCMeta, abstractmethod
from dataclasses import dataclass, asdict, fields, MISSING
from pathlib import Path
from typing import Optional

# Dictionary of all locator typenames to class instances
TYPES = {}


class LocatorMeta(ABCMeta):
    """Metaclass for keeping track of all locator types."""

    def __new__(cls, name, bases, namespace, **kwargs):
        locator = super().__new__(cls, name, bases, namespace, **kwargs)
        if name != "Locator":
            TYPES[locator().typename] = locator
        return locator


@dataclass
class Locator(metaclass=LocatorMeta):
    """Baseclass for a locator entry."""

    @staticmethod
    def from_dict(data):
        """Construct correct locator subclass from dictionary,
        which should contain a 'type' field and at least all
        required fields of that locator.
        """
        type_ = data.pop("type", None)
        if not type_:
            raise ValueError("Missing locator type field")

        class_ = TYPES.get(type_)
        if not class_:
            raise ValueError(f"Unknown locator type: {type_}")

        # Check for missing parameters
        required = set(
            field.name for field in fields(class_) if field.default is MISSING
        )
        missing = set(required) - set(data)
        if missing:
            raise ValueError("Missing locator field(s): {}".format(", ".join(missing)))

        # Ignore extra data
        required_or_optional = [field.name for field in fields(class_)]
        kwargs = {k: v for k, v in data.items() if k in required_or_optional}

        return class_(**kwargs)

    def to_dict(self):
        """Convert locator instance to a dictionary with type information."""
        data = {"type": self.typename}

        for key, value in asdict(self).items():
            if isinstance(value, Path):
                value = str(value)
            data[key] = value

        return data

    @property
    @abstractmethod
    def typename(self):
        """Name of locator type used in serialization."""
        raise NotImplementedError


@dataclass
class ImageTemplate(Locator):
    """Image-based locator for template matching."""

    path: Path
    confidence: Optional[float] = None
    source: Optional[Path] = None  # TODO: Remove when crop is implemented

    @property
    def typename(self):
        return "image"

    def __post_init__(self):
        if self.confidence is not None:
            self.confidence = float(self.confidence)


@dataclass
class BrowserDOM(Locator):
    """Browser-based locator for DOM elements."""

    strategy: str
    value: str
    source: Optional[str] = None
    screenshot: Optional[Path] = None

    @property
    def typename(self):
        return "browser"


@dataclass
class Coordinates(Locator):
    """Locator for absolute coordinates."""

    x: int
    y: int

    @property
    def typename(self):
        return "coordinates"

    def __post_init__(self):
        self.x = int(self.x)
        self.y = int(self.y)


@dataclass
class Offset(Locator):
    """Locator for offset coordinates."""

    x: int
    y: int

    @property
    def typename(self):
        return "offset"

    def __post_init__(self):
        self.x = int(self.x)
        self.y = int(self.y)
