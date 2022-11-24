"""Common utilities shared by any e-mail related library."""


import base64
import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional, Union

from RPA.MFA import MFA


lib_mfa = MFA()

OAuthProviderType = Union["OAuthProvider", str]


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


class OAuthMixin:
    """Common keywords for the Email libraries, enabling OAuth2 support."""

    def __init__(self, provider: OAuthProviderType, tenant: Optional[str]):
        self._oauth_provider = OAUTH_PROVIDERS[OAuthProvider(provider)]
        if tenant:
            for url_attr in ("auth_url", "token_url"):
                formatted = getattr(self._oauth_provider, url_attr).format(
                    tenant=tenant
                )
                setattr(self._oauth_provider, url_attr, formatted)
        # NOTE(cmin764): https://github.com/requests/requests-oauthlib/issues/387#issuecomment-1325131664
        os.environ["OAUTHLIB_RELAX_TOKEN_SCOPE"] = "1"

    def generate_oauth_url(self, client_id: str) -> str:
        """Generates an authorization URL which must be opened by the user to start the
        OAuth2 flow and obtain an authorization code as response.
        """
        return lib_mfa.generate_oauth_url(
            self._oauth_provider.auth_url,
            client_id=client_id,
            redirect_uri=self._oauth_provider.redirect_uri,
            scope=self._oauth_provider.scope,
        )

    def get_oauth_token(self, client_secret: str, response_url: str) -> dict:
        """Exchanges the code obtained previously with `Generate OAuth URL` for a
        token.
        """
        return lib_mfa.get_oauth_token(
            self._oauth_provider.token_url,
            client_secret=client_secret,
            response_url=response_url,
            include_client_id=True,
        )

    def refresh_oauth_token(
        self, client_id: str, client_secret: str, token: dict
    ) -> dict:
        return lib_mfa.refresh_oauth_token(
            self._oauth_provider.token_url,
            client_id=client_id,
            client_secret=client_secret,
            refresh_token=token["refresh_token"],
        )

    def generate_oauth_string(self, username: str, access_token: str) -> str:
        auth_string = f"user={username}\1auth=Bearer {access_token}\1\1"
        return base64.b64encode(auth_string.encode()).decode()


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
