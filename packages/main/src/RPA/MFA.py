from enum import Enum
import logging
from typing import Optional
from pyotp import HOTP, TOTP
from robot.api.deco import keyword
from RPA.Robocorp.Vault import Vault


class OTPMode(Enum):
    """Enumeration for type of TOP to use"""

    TIME = "TIME"
    COUNTER = "COUNTER"


class TOTPNotSetError(Exception):
    "Error when TOTP (Time-based One-Time Password) has not been set"


class HOTPNotSetError(Exception):
    "Error when HOTP (HMAC One-Time Password) has not been set"


TOTP_NOT_SET_ERROR_MSG = """TOTP (Time-based One-Time Password) can be set in library initialization, with
`Use MFA Secret From Vault` keyword or with `Set Time Based OTP` keyword."""

HOTP_NOT_SET_ERROR_MSG = """HOTP (HMAC One-Time Password) can be set in library initialization, with
`Use MFA Secret From Vault` keyword or with `Set Counter Based OTP` keyword."""


class MFA:
    """*RPA.MFA* is a library for generating one-time passwords (OTP).

    Based on the `pyotp <https://pypi.org/project/pyotp/>`_ package.


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
        self._hotp = None
        self._totp = None
        if vault_name and vault_key:
            self.use_mfa_secret_from_vault(vault_name, vault_key, mode)

    @keyword
    def use_mfa_secret_from_vault(
        self, vault_name: str, vault_key: str, mode: OTPMode = OTPMode.TIME
    ):
        """_summary_

        :param vault_name: _description_
        :param vault_key: _description_
        """
        secrets = Vault().get_secret(vault_name)
        if mode == OTPMode.TIME:
            self.set_time_based_otp(secrets[vault_key])
        elif mode == OTPMode.COUNTER:
            self.set_counter_based_otp(secrets[vault_key])

    @keyword
    def set_time_based_otp(self, base_secret_key: str):
        """_summary_

        :param base_secret_key: _description_
        """
        self._totp = TOTP(base_secret_key)

    @keyword
    def set_counter_based_otp(self, base_secret_key: str):
        """_summary_

        :param base_secret_key: _description_
        """
        self._hotp = HOTP(base_secret_key)

    @keyword
    def get_time_based_otp(self, base_secret_key: Optional[str] = None):
        """_summary_

        :param base_secret_key: _description_, defaults to None
        :raises TOTPNotSetError: _description_
        :return: _description_
        """
        if base_secret_key:
            self.set_time_based_otp(base_secret_key)
        if not self._totp:
            raise TOTPNotSetError(TOTP_NOT_SET_ERROR_MSG)
        return self._totp.now()

    @keyword
    def get_counter_based_otp(
        self,
        counter: int,
        base_secret_key: Optional[str] = None,
    ):
        """_summary_

        :param counter: _description_
        :param base_secret_key: _description_, defaults to None
        :raises HOTPNotSetError: _description_
        :return: _description_
        """
        if base_secret_key:
            self.set_counter_based_otp(base_secret_key)
        if not self._hotp:
            raise HOTPNotSetError(HOTP_NOT_SET_ERROR_MSG)
        return self._hotp.at(counter)
