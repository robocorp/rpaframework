import importlib
import json
import os
import tempfile

from apiclient import discovery
from google.oauth2 import service_account as oauth_service_account
from google.protobuf.json_format import MessageToJson

try:
    from robot.libraries.BuiltIn import BuiltIn
except ModuleNotFoundError:
    BuiltIn = None

secrets_library = None
try:
    Secrets = importlib.import_module("RPA.Robocloud.Secrets")
    secrets_library = Secrets()
except ModuleNotFoundError:
    if BuiltIn:
        secrets_library = BuiltIn().get_library_instance("RPA.Robocloud.Secrets")


class ElementNotFound(ValueError):
    """No matching elements were found."""


class MultipleElementsFound(ValueError):
    """Multiple matching elements were found, but only one was expected."""


class TimeoutException(ValueError):
    """Timeout reached while waiting for condition."""


class GoogleOAuthAuthenticationError(Exception):
    """Raised when unable to get Google OAuth credentials."""


class LibraryContext:
    """Shared context for all keyword libraries."""

    def __init__(self, ctx):
        self.ctx = ctx

    @property
    def logger(self):
        return self.ctx.logger

    @property
    def robocloud_vault_name(self):
        return self.ctx.robocloud_vault_name

    @property
    def robocloud_vault_secret_key(self):
        return self.ctx.robocloud_vault_secret_key

    @property
    def service_account_file(self):
        return self.ctx.service_account_file

    def get_service_account_from_robocloud(self):
        if secrets_library is None:
            raise KeyError("RPA.Robocloud.Secrets library is required use Vault")
        temp_filedesc = None
        if self.robocloud_vault_name is None or self.robocloud_vault_secret_key is None:
            raise KeyError(
                "Both 'robocloud_vault_name' and 'robocloud_vault_secret_key' "
                "are required to access Robocloud Vault. Set them in library "
                "init or with `set_robocloud_vault` keyword."
            )
        vault_items = Secrets.get_secret(self.robocloud_vault_name)
        secret_dict = vault_items[self.robocloud_vault_secret_key]
        secret = (
            secret_dict
            if isinstance(secret_dict, dict)
            else json.loads(secret_dict.strip())
        )
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as temp_filedesc:
            json.dump(secret, temp_filedesc, ensure_ascii=False)

        return temp_filedesc.name

    def init_service(
        self,
        service_name: str,
        api_version: str,
        scopes: list,
        service_account: str = None,
        use_robocloud_vault: bool = False,
        token_file: str = None,
        save_token: bool = False,
    ) -> None:
        """Initialize Google Service

        :param service_account: filepath to credentials JSON
        :param use_robocloud_vault: use json stored into `Robocloud Vault`
        """
        service = None
        service_account_file = None
        if use_robocloud_vault:
            service_account_file = self.get_service_account_from_robocloud()
            credentials = oauth_service_account.Credentials.from_service_account_file(
                service_account_file, scopes=scopes
            )
        elif service_account or self.service_account_file:
            service_account_file = service_account or self.service_account_file
            credentials = oauth_service_account.Credentials.from_service_account_file(
                service_account_file, scopes=scopes
            )
        elif token_file:
            self.logger.info("save_token: %s", save_token)
            raise NotImplementedError
            # credentials = self._get_credentials_with_oauth_token(
            #     use_robocloud_vault,
            #     token_file,
            #     service_account,
            #     scopes,
            #     save_token,
            # )

        else:
            raise AttributeError(
                "Either 'service_credentials_file' "
                "or 'use_robocloud_vault' needs to be set"
            )
        try:
            credentials = oauth_service_account.Credentials.from_service_account_file(
                service_account_file, scopes=scopes
            )
            service = discovery.build(
                service_name,
                api_version,
                credentials=credentials,
                cache_discovery=False,
            )
        except OSError as e:
            raise AssertionError from e
        finally:
            if use_robocloud_vault:
                os.remove(service_account_file)
        return service

    def init_service_with_object(
        self, client_object, service_account, use_robocloud_vault
    ):
        service = None
        if use_robocloud_vault:
            try:
                service_account_file = self.get_service_account_from_robocloud()
                service = client_object.from_service_account_json(service_account_file)
            finally:
                if service_account_file:
                    os.remove(service_account_file)
        elif service_account or self.service_account_file:
            service_account_file = service_account or self.service_account_file
            service = client_object.from_service_account_json(service_account_file)
        else:
            service = client_object()
        return service

    def write_json(self, json_file, response):
        if json_file and response:
            with open(json_file, "w") as f:
                f.write(MessageToJson(response))
