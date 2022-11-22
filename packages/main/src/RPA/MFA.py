import logging
from enum import Enum
from typing import List, Optional

import jwt
from pyotp import HOTP, TOTP
from requests_oauthlib import OAuth2Session
from robot.api.deco import keyword

from RPA.Robocorp.Vault import Vault


class OTPMode(Enum):
    """Enumeration for type of OTP to use."""

    TIME = "TIME"
    COUNTER = "COUNTER"


class TOTPNotSetError(Exception):
    """Raised when TOTP (Time-based One-Time Password) has not been set."""

    ERROR_MSG = (
        "TOTP (Time-based One-Time Password) can be set during the library "
        "initialization. With `Use MFA Secret From Vault` keyword or with "
        "`Set Time Based OTP` keyword."
    )


class HOTPNotSetError(Exception):
    """Raised when HOTP (HMAC One-Time Password) has not been set."""

    ERROR_MSG = (
        "HOTP (HMAC One-Time Password) can be set during the library "
        "initialization. With `Use MFA Secret From Vault` keyword or with "
        "`Set Counter Based OTP` keyword."
    )


class OAuth2NotSetError(Exception):
    """Raised when OAuth2 session object isn't initialized but used."""

    ERROR_MSG = (
        "OAuth2 session required but not initialized, please call the "
        "`Generate OAuth URL` keyword first."
    )


class MFA:
    """*RPA.MFA* is a library intended mainly for generating one-time passwords (OTP).

    Added on **rpaframework** version: 19.3.0

    Based on the `pyotp <https://pypi.org/project/pyotp/>`_ package.

    In the below example the **mfa** secret we are reading from the Robocorp
    Vault is the passcode generated by the Authenticator service. The passcode
    value is stored into the Vault with key **otpsecret**.

    Passcode is typically a long string (16-32 characters), which is provided
    in a form of QR image, but it can be obtained by requesting access to a string.

    Note that same code can be used to add a mobile phone as a authentication
    device at the same as the same code is added into the Vault.

    **Robot framework example usage:**

    .. code-block:: robotframework

        *** Settings ***
        Library     RPA.Robocorp.Vault
        Library     RPA.MFA


        *** Tasks ***
        Generate time based code
            ${secrets}=    Get Secret   mfa
            ${code}=    Get Time Based OTP    ${secrets}[otpsecret]


    **Python example usage**

    .. code-block:: python

        from RPA.Robocorp.Vault import Vault
        from RPA.MFA import MFA


        def main():
            secrets = Vault().get_secret("mfa")
            code = MFA().get_time_based_otp(secrets["otpsecret"])
    """

    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    ROBOT_LIBRARY_DOC_FORMAT = "REST"

    def __init__(
        self,
        vault_name: Optional[str] = None,
        vault_key: Optional[str] = None,
        mode: Optional[OTPMode] = OTPMode.TIME,
    ):
        self.logger = logging.getLogger(__name__)
        self._hotp: Optional[HOTP] = None
        self._totp: Optional[TOTP] = None
        if vault_name and vault_key:
            self.use_mfa_secret_from_vault(vault_name, vault_key, mode)
        self._oauth: Optional[OAuth2Session] = None

    @keyword
    def use_mfa_secret_from_vault(
        self, vault_name: str, vault_key: str, mode: OTPMode = OTPMode.TIME
    ):
        """Set `time` or `counter` based OTP with passcode stored in
        the Robocorp Vault named with `vault_name` under key of `vault_key`.

        :param vault_name: name of the vault storing the passcode
        :param vault_key: name of the vault key storing the passcode value
        """
        secrets = Vault().get_secret(vault_name)
        if mode == OTPMode.TIME:
            self.set_time_based_otp(secrets[vault_key])
        elif mode == OTPMode.COUNTER:
            self.set_counter_based_otp(secrets[vault_key])

    @keyword
    def set_time_based_otp(self, otp_passcode: str):
        """Set `time` based OTP with passcode.

        :param otp_passcode: the passcode provided by the Authenticator
        """
        self._totp = TOTP(otp_passcode)

    @keyword
    def set_counter_based_otp(self, otp_passcode: str):
        """Set `counter` based OTP with passcode.

        :param otp_passcode: the passcode provided by the Authenticator
        """
        self._hotp = HOTP(otp_passcode)

    @keyword
    def get_time_based_otp(self, otp_passcode: Optional[str] = None):
        """Get `time` based one time password using separately set
        passcode or by parameter `otp_passcode`.

        :param otp_passcode: the passcode provided by the Authenticator
        """
        if otp_passcode:
            self.set_time_based_otp(otp_passcode)
        if not self._totp:
            raise TOTPNotSetError(TOTPNotSetError.ERROR_MSG)
        return self._totp.now()

    @keyword
    def get_counter_based_otp(
        self,
        counter: int,
        otp_passcode: Optional[str] = None,
    ):
        """Get `counter` based one time password using separately set
        passcode or by parameter `otp_passcode`. The counter index is
        given by the `counter` parameter.

        :param counter: the index of the counter
        :param otp_passcode: the passcode provided by the Authenticator
        """
        if otp_passcode:
            self.set_counter_based_otp(otp_passcode)
        if not self._hotp:
            raise HOTPNotSetError(HOTPNotSetError.ERROR_MSG)
        return self._hotp.at(counter)

    @property
    def oauth(self) -> OAuth2Session:
        if not self._oauth:
            raise OAuth2NotSetError(OAuth2NotSetError.ERROR_MSG)

        return self._oauth

    @keyword
    def generate_oauth_url(
        self, auth_url: str, *, client_id: str, redirect_uri: str, scope: str
    ) -> str:
        """Generates an authorization URL which must be opened by the user to start the
        OAuth2 flow and obtain an authorization code as response.
        """
        scopes: List[str] = scope.split()
        self._oauth = OAuth2Session(client_id, redirect_uri=redirect_uri, scope=scopes)
        authorization_url, _ = self.oauth.authorization_url(auth_url)
        return authorization_url

    @keyword
    def authorize_and_get_token(
        self, token_url: str, *, client_secret: str, auth_code: str
    ) -> dict:
        """Exchanges the code obtained previously with `Generate OAuth URL` for a
        token.
        """
        token = self.oauth.fetch_token(
            token_url, client_secret=client_secret, code=auth_code
        )
        return token
