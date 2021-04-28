from enum import Enum

from . import (
    LibraryContext,
    keyword,
)


class TextType(Enum):
    """Possible text types."""

    TEXT = "text/plain"
    HTML = "text/html"


def to_texttype(value):
    """Convert value to TextType enum."""
    if isinstance(value, TextType):
        return value

    sanitized = str(value).upper().strip().replace(" ", "_")
    try:
        return TextType[sanitized]
    except KeyError as err:
        raise ValueError(f"Unknown text type: {value}") from err


class BaseKeywords(LibraryContext):
    """Base keywords for the Google library"""

    @keyword
    def set_robocorp_vault(
        self,
        vault_name: str = None,
        vault_secret_key: str = None,
        auth_type: str = "serviceaccount",
    ):
        """Set Robocloud Vault name and secret key name
        :param vault_name: Robocloud Vault name
        :param vault_secret_key: Rococloud Vault secret key name
        """
        if vault_name:
            self.robocorp_vault_name = vault_name
        if vault_secret_key:
            self.robocorp_vault_secret_key = vault_secret_key
        if self.robocorp_vault_name and self.robocorp_vault_secret_key:
            self.use_robocorp_vault = True
        self.robocloud_auth_type = auth_type
