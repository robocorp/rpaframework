from . import (
    LibraryContext,
    keyword,
)


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
        self.cloud_auth_type = auth_type
