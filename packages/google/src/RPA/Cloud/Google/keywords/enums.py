from enum import Enum


class TextType(Enum):
    """Possible text types."""

    TEXT = "text/plain"
    HTML = "text/html"


class UpdateAction(Enum):
    """Possible file update actions."""

    trash = 1
    untrash = 2
    star = 3
    unstar = 4


def to_texttype(value):
    """Convert value to TextType enum."""
    if isinstance(value, TextType):
        return value

    sanitized = str(value).upper().strip().replace(" ", "_")
    try:
        return TextType[sanitized]
    except KeyError as err:
        raise ValueError(f"Unknown text type: {value}") from err