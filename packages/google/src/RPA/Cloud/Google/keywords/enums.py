from enum import Enum
from google.cloud import language_v1, videointelligence


class TextType(Enum):
    """Possible text types."""

    TEXT = language_v1.Document.Type.PLAIN_TEXT
    HTML = language_v1.Document.Type.HTML


class UpdateAction(Enum):
    """Possible file update actions."""

    trash = 1
    untrash = 2
    star = 3
    unstar = 4


def to_texttype(value):
    """Convert value to TextType enum."""
    if isinstance(value, TextType):
        return int(value.value)

    sanitized = str(value).upper().strip().replace(" ", "_")
    try:
        return int(TextType[sanitized].value)
    except KeyError as err:
        raise ValueError(f"Unknown text type: {value}") from err


class VideoFeature(Enum):
    """Possible video features."""

    FEATURE_UNSPECIFIED = videointelligence.Feature.FEATURE_UNSPECIFIED
    LABEL_DETECTION = videointelligence.Feature.LABEL_DETECTION
    SHOT_CHANGE_DETECTION = videointelligence.Feature.SHOT_CHANGE_DETECTION
    EXPLICIT_CONTENT_DETECTION = videointelligence.Feature.EXPLICIT_CONTENT_DETECTION
    SPEECH_TRANSCRIPTION = videointelligence.Feature.SPEECH_TRANSCRIPTION
    TEXT_DETECTION = videointelligence.Feature.TEXT_DETECTION
    OBJECT_TRACKING = videointelligence.Feature.OBJECT_TRACKING
    LOGO_RECOGNITION = videointelligence.Feature.LOGO_RECOGNITION


def to_feature(value):
    """Convert value to VideoFeature enum."""
    if isinstance(value, VideoFeature):
        return int(value.value)

    sanitized = str(value).upper().strip().replace(" ", "_")
    try:
        return int(VideoFeature[sanitized].value)
    except KeyError as err:
        raise ValueError(f"Unknown video feature: {value}") from err


class DriveRole(Enum):
    """Possible Drive user roles"""

    OWNER = "owner"
    ORGANIZER = "organizer"
    FILE_ORGANIZER = "fileOrganizer"
    WRITER = "writer"
    COMMENTER = "commenter"
    READER = "reader"


def to_drive_role(value):
    """Convert value to DriveRole enum."""
    if isinstance(value, DriveRole):
        return value.value

    sanitized = str(value).upper().strip().replace(" ", "_")
    try:
        return DriveRole[sanitized].value
    except KeyError as err:
        raise ValueError(f"Unknown drive role: {value}") from err


class DriveType(Enum):
    """Possible Drive Share types"""

    USER = "user"
    GROUP = "group"
    DOMAIN = "domain"
    ANY = "anyone"


def to_drive_type(value):
    """Convert value to DriveType enum."""
    if isinstance(value, DriveType):
        return value.value

    sanitized = str(value).upper().strip().replace(" ", "_")
    try:
        return DriveType[sanitized].value
    except KeyError as err:
        raise ValueError(f"Unknown drive type: {value}") from err
