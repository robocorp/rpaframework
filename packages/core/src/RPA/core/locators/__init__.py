# flake8: noqa
from dataclasses import fields
from .containers import (
    TYPES,
    Locator,
    PointLocator,
    OffsetLocator,
    RegionLocator,
    SizeLocator,
    ImageLocator,
    OcrLocator,
    BrowserLocator,
    # For backwards compatibility:
    Coordinates,
    Offset,
    BrowserDOM,
    ImageTemplate,
)
from .database import LocatorsDatabase, sanitize_name
from .literal import LocatorType
