from RPA.Cloud.Google.keywords import (
    LibraryContext,
    keyword,
)


class BaseKeywords(LibraryContext):
    """Base keywords for the Google library"""

    @keyword
    def set_robocloud_vault(self, vault_name: str = None, vault_secret_key: str = None):
        """Set Robocloud Vault name and secret key name
        :param vault_name: Robocloud Vault name
        :param vault_secret_key: Rococloud Vault secret key name
        """
        if vault_name:
            self.robocloud_vault_name = vault_name
        if vault_secret_key:
            self.robocloud_vault_secret_key = vault_secret_key
