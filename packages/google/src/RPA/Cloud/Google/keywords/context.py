from google.oauth2 import service_account
import json
import tempfile


class ElementNotFound(ValueError):
    """No matching elements were found."""


class MultipleElementsFound(ValueError):
    """Multiple matching elements were found, but only one was expected."""


class TimeoutException(ValueError):
    """Timeout reached while waiting for condition."""


class LibraryContext:
    """Shared context for all keyword libraries."""

    def __init__(self, ctx):
        self.ctx = ctx

    @property
    def logger(self):
        return self.ctx.logger

    def get_service_account_from_robocloud(self):
        temp_filedesc = None
        if (
            self.ctx.robocloud_vault_name is None
            or self.ctx.robocloud_vault_secret_key is None
        ):
            raise KeyError(
                "Both 'robocloud_vault_name' and 'robocloud_vault_secret_key' "
                "are required to access Robocloud Vault. Set them in library "
                "init or with `set_robocloud_vault` keyword."
            )
        # Get instance of RPA.Robocloud.Secrets
        vault = Secrets()

        vault_items = vault.get_secret(self.ctx.robocloud_vault_name)
        secret = json.loads(vault_items[self.ctx.robocloud_vault_secret_key].strip())
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as temp_filedesc:
            json.dump(secret, temp_filedesc, ensure_ascii=False)

        return temp_filedesc.name
