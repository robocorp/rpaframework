from dataclasses import dataclass, asdict, fields, MISSING
from typing import Optional


@dataclass
class Locator:
    """Baseclass for a locator entry."""

    def __str__(self):
        values = []
        for field in fields(self):
            if field.default is not MISSING:
                break
            values.append(getattr(self, field.name))

        typename = NAMES[type(self)]
        return "{}:{}".format(typename, ",".join(str(value) for value in values))

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
        data = {"type": NAMES[type(self)]}
        data.update(asdict(self))
        return data


@dataclass
class PointLocator(Locator):
    """Locator for absolute coordinates."""

    x: int
    y: int

    def __post_init__(self):
        self.x = int(self.x)
        self.y = int(self.y)


@dataclass
class OffsetLocator(Locator):
    """Locator for offset coordinates."""

    x: int
    y: int

    def __post_init__(self):
        self.x = int(self.x)
        self.y = int(self.y)


@dataclass
class RegionLocator(Locator):
    """Locator for area defined by coordinates."""

    left: int
    top: int
    right: int
    bottom: int

    def __post_init__(self):
        self.left = int(self.left)
        self.top = int(self.top)
        self.right = int(self.right)
        self.bottom = int(self.bottom)


@dataclass
class SizeLocator(Locator):
    """Locator for area defined by width/height."""

    width: int
    height: int

    def __post_init__(self):
        self.width = int(self.width)
        self.height = int(self.height)


@dataclass
class ImageLocator(Locator):
    """Image-based locator for template matching."""

    path: str
    confidence: Optional[float] = None
    source: Optional[str] = None  # TODO: Remove when crop is implemented

    def __post_init__(self):
        if self.confidence is not None:
            self.confidence = float(self.confidence)


@dataclass
class OcrLocator(Locator):
    """Locator for OCR-based text."""

    text: str
    confidence: Optional[float] = None
    """3-character ISO 639-2 language code. Passed to pytesseract lang parameter."""
    language: Optional[str] = None

    def __post_init__(self):
        self.text = str(self.text)
        if self.confidence is not None:
            self.confidence = float(self.confidence)


@dataclass
class BrowserLocator(Locator):
    """Browser-based locator for DOM elements."""

    strategy: str
    value: str
    source: Optional[str] = None
    screenshot: Optional[str] = None


@dataclass
class WindowsLocator(Locator):
    """Windows-based locator for windows UI elements"""

    window: str
    value: str
    version: float
    screenshot: Optional[str] = None


# Aliases for backwards compatibility, just in case.
Offset = OffsetLocator
BrowserDOM = BrowserLocator
ImageTemplate = ImageLocator
Coordinates = PointLocator

# Mapping of supported locator typenames to classes.
# Used for parsing locator literals.
TYPES = {
    "point": PointLocator,
    "offset": OffsetLocator,
    "region": RegionLocator,
    "size": SizeLocator,
    "image": ImageLocator,
    "ocr": OcrLocator,
    "browser": BrowserLocator,
    "coordinates": PointLocator,  # Backwards compatibility
    "windows": WindowsLocator,
}

# Above mapping but in reverse direction.
NAMES = {
    PointLocator: "point",
    OffsetLocator: "offset",
    RegionLocator: "region",
    SizeLocator: "size",
    ImageLocator: "image",
    OcrLocator: "ocr",
    BrowserLocator: "browser",
    PointLocator: "point",  # Backwards compatibility
    WindowsLocator: "windows",
}
