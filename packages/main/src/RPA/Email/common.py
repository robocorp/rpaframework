"""Common utilities shared by any e-mail related library."""


from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class OAuthProvider(Enum):
    """OAuth2 tested providers."""

    GOOGLE = "google"
    MICROSOFT = "microsoft"


@dataclass
class OAuthConfig:

    auth_url: str
    redirect_uri: str
    scope: str
    token_url: str


OAUTH_PROVIDERS = {
    OAuthProvider.GOOGLE: OAuthConfig(
        auth_url="https://accounts.google.com/o/oauth2/auth",
        redirect_uri="urn:ietf:wg:oauth:2.0:oob",
        scope="https://mail.google.com",
        token_url="https://accounts.google.com/o/oauth2/token",
    ),
    OAuthProvider.MICROSOFT: OAuthConfig(
        auth_url="https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize",
        redirect_uri="https://login.microsoftonline.com/common/oauth2/nativeclient",
        scope="offline_access https://outlook.office365.com/.default",
        token_url="https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token",
    ),
}


def counter_duplicate_path(file_path: Path) -> Path:
    """Returns a unique file path by adding a suffixed counter if already exists."""
    if not file_path.exists():
        return file_path  # unique already

    root_dir = file_path.parent
    duplicates = root_dir.glob(f"{file_path.stem}*{file_path.suffix}")
    suffixes = []
    for dup in duplicates:
        parts = dup.stem.rsplit("-", 1)
        if len(parts) == 2 and parts[1].isdigit():
            suffixes.append(int(parts[1]))
    next_suffix = max(suffixes) + 1 if suffixes else 2

    file_path = root_dir / f"{file_path.stem}-{next_suffix}{file_path.suffix}"
    return file_path
