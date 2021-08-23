# pylint: disable=unused-import
# flake8: noqa
import logging
from RPA.Robocorp.Vault import (
    Secret,
    BaseSecretManager,
    FileSecrets,
    RobocorpVault as RobocloudVault,
    RobocorpVaultError as RobocloudVaultError,
    Vault as _Vault,
)


class Secrets(_Vault):
    __doc__ = _Vault.__doc__

    def __init__(self, *args, **kwargs):
        logging.warning(
            "This is a deprecated import that will "
            "be removed in favor of RPA.Robocorp.Vault"
        )
        super().__init__(*args, **kwargs)
