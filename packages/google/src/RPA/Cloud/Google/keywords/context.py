import base64
import json
import os
from pathlib import Path
import pickle
import tempfile

from apiclient import discovery
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2 import service_account as oauth_service_account


try:
    from robot.libraries.BuiltIn import BuiltIn
except ModuleNotFoundError:
    BuiltIn = None

try:
    from RPA.Robocloud.Secrets import Secrets
except ModuleNotFoundError:
    Secrets = None


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
    def robocorp_vault_name(self):
        return self.ctx.robocorp_vault_name

    @property
    def robocorp_vault_secret_key(self):
        return self.ctx.robocorp_vault_secret_key

    @property
    def use_robocorp_vault(self):
        return self.ctx.use_robocorp_vault

    @property
    def service_account_file(self):
        return self.ctx.service_account_file

    @property
    def cloud_auth_type(self):
        return self.ctx.cloud_auth_type

    def get_from_robocorp_vault(self, secret_type="serviceaccount"):
        secret_library = Secrets
        try:
            if secret_library is None and BuiltIn:
                secret_library = BuiltIn().get_library_instance("RPA.Robocloud.Secrets")
        except RuntimeError as runtime_error:
            raise KeyError(
                "RPA.Robocloud.Secrets library is required use Vault"
            ) from runtime_error
        temp_filedesc = None
        if (
            self.ctx.robocorp_vault_name is None
            or self.ctx.robocorp_vault_secret_key is None
        ):
            raise KeyError(
                "Both 'robocorp_vault_name' and 'robocorp_vault_secret_key' "
                "are required to access Robocloud Vault. Set them in library "
                "init or with `set_robocloud_vault` keyword."
            )
        vault_items = secret_library().get_secret(self.ctx.robocorp_vault_name)
        secret = vault_items[self.ctx.robocorp_vault_secret_key]
        if secret_type == "serviceaccount":
            secret_obj = (
                secret if isinstance(secret, dict) else json.loads(secret.strip())
            )
            with tempfile.NamedTemporaryFile(mode="w", delete=False) as temp_filedesc:
                json.dump(secret_obj, temp_filedesc, ensure_ascii=False)

            return temp_filedesc.name
        else:
            return secret

    def init_service(
        self,
        service_name: str,
        api_version: str,
        scopes: list,
        service_account_file: str = None,
        credentials_file: str = None,
        use_robocorp_vault: bool = False,
        token_file: str = None,
        save_token: bool = False,
        auth_type: str = None,
    ) -> None:
        """Initialize Google Service

        :param service_account: filepath to credentials JSON
        :param use_robocloud_vault: use json stored into `Robocloud Vault`
        """
        service = None
        if use_robocorp_vault is not None:
            use_cloud = bool(use_robocorp_vault)
        else:
            use_cloud = self.ctx.use_robocorp_vault
        if use_cloud:
            cloud_auth_type = auth_type or self.ctx.cloud_auth_type
            if cloud_auth_type == "serviceaccount":
                self.logger.info(
                    "Authenticating with service account file from Robocorp Vault"
                )
                service_account_file = self.get_from_robocorp_vault("serviceaccount")
                credentials = (
                    oauth_service_account.Credentials.from_service_account_file(
                        service_account_file, scopes=scopes
                    )
                )
            else:
                self.logger.info(
                    "Authenticating with oauth token file from Robocorp Vault"
                )
                credentials = self.get_credentials_with_oauth_token(
                    use_cloud,
                    token_file,
                    credentials_file,
                    scopes,
                    save_token,
                )
        elif service_account_file or self.ctx.service_account_file:
            self.logger.info("Authenticating with service account file")
            service_account_file = service_account_file or self.service_account_file
            credentials = oauth_service_account.Credentials.from_service_account_file(
                service_account_file, scopes=scopes
            )
        elif token_file:
            self.logger.info("Authenticating with oauth token file")
            token_file_location = Path(token_file).absolute()
            if os.path.exists(token_file_location):
                with open(token_file_location, "rb") as token:
                    credentials = pickle.loads(token)
        else:
            raise AttributeError(
                "Either 'service_credentials_file' "
                "or 'use_robocorp_vault' needs to be set"
            )
        if credentials is None:
            raise AssertionError(
                "Failed to create credentials for service '%s'" % service_name
            )
        try:
            service = discovery.build(
                service_name,
                api_version,
                credentials=credentials,
                cache_discovery=False,
            )
        except OSError as e:
            raise AssertionError from e

        return service

    def init_service_with_object(
        self,
        client_object: str,
        service_account_file: str,
        use_robocorp_vault: bool,
        token_file: str = None,
        auth_type: str = None,
    ):
        service = None
        if use_robocorp_vault is not None:
            robocloud = bool(use_robocorp_vault)
        else:
            robocloud = self.ctx.use_robocorp_vault

        cloud_auth_type = auth_type or self.ctx.cloud_auth_type
        if robocloud:
            if cloud_auth_type == "serviceaccount":
                try:
                    self.logger.info(
                        "Authenticating with service account file from Robocloud"
                    )
                    service_account_file = self.get_from_robocorp_vault(
                        "serviceaccount"
                    )
                    service = client_object.from_service_account_json(
                        service_account_file
                    )
                finally:
                    if service_account_file:
                        os.remove(service_account_file)
            else:
                self.logger.info("Authenticating with oauth token file from Robocloud")
                token = self.get_from_robocorp_vault("token")
                credentials = pickle.loads(base64.b64decode(token))
                service = client_object(credentials=credentials)
        elif service_account_file or self.ctx.service_account_file:
            self.logger.info("Authenticating with service account file")
            service_account_file = service_account_file or self.ctx.service_account_file
            service = client_object.from_service_account_json(service_account_file)
        elif token_file:
            self.logger.info("Authenticating with oauth token file")
            token_file_location = Path(token_file).absolute()
            if os.path.exists(token_file_location):
                with open(token_file_location, "rb") as token:
                    credentials = pickle.loads(token)
                    service = client_object(credentials=credentials)
        else:
            self.logger.info("Authenticating with default client object")
            service = client_object()
        if service is None:
            raise AssertionError("Failed to create client: '%s'" % client_object)
        return service

    def write_json(self, json_file, response):
        if json_file and response:
            with open(json_file, "w") as f:
                f.write(response.__class__.to_json(response))

    def get_credentials_with_oauth_token(
        self, use_robocorp_vault, token_file, credentials_file, scopes, save_token
    ):
        credentials = None
        if use_robocorp_vault:
            token = self.get_from_robocorp_vault("token")
            credentials = pickle.loads(base64.b64decode(token))
        else:
            token_file_location = Path(token_file).absolute()
            if os.path.exists(token_file_location):
                with open(token_file_location, "rb") as token:
                    credentials = pickle.loads(token)

        if not credentials or not credentials.valid:
            scopes = [f"https://www.googleapis.com/auth/{scope}" for scope in scopes]
            if credentials and credentials.expired and credentials.refresh_token:
                credentials.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    credentials_file, scopes
                )
                credentials = flow.run_local_server()
            if save_token:
                with open(token_file_location, "wb") as token:
                    pickle.dump(credentials, token)
        if not credentials:
            raise GoogleOAuthAuthenticationError(
                "Could not get Google OAuth credentials"
            )
        return credentials
