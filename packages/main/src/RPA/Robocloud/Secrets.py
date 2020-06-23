import importlib
import json
import os
from abc import abstractmethod, ABCMeta

import requests
from robot.libraries.BuiltIn import BuiltIn, RobotNotRunningError


class RobocloudVaultError(Exception):
    """Raised when there is problem with Robocloud Vault secrets"""


class Secrets:
    """Handler for SecretManager. Decides which SecretManager to use based on
    environment variable `RPA_SECRET_MANAGER`. If environment variable is not
    defined then `RobocloudSecrets` is used as default SecretManager.

    :raises Exception: if configured SecretManager does not implement
                       `BaseSecretManager` class
    :raises Exception: if configured SecretManager does not exist in the namespace
    """

    def __init__(self, *args):
        try:
            BuiltIn().import_library("RPA.RobotLogListener")
        except RobotNotRunningError:
            pass

        self.secretmanager = os.getenv(
            "RPA_SECRET_MANAGER", "RPA.Robocloud.Secrets.RobocloudVault"
        )
        package, modulename = self.secretmanager.rsplit(".", 1)
        module = importlib.import_module(package)
        my_class = getattr(module, modulename)
        if args:
            self.secretmanager_obj = my_class(args)
        else:
            self.secretmanager_obj = my_class()

    def __getattr__(self, name):
        if self.secretmanager_obj is not None:
            return getattr(self.secretmanager_obj, name)
        raise AttributeError("No valid backend")

    def get_keyword_names(self):
        return ["get_secret"]


class BaseSecretManager(metaclass=ABCMeta):
    """Abstract class for Secret management which should be used as a
    base class for any Secrets implementation class.

    """

    @abstractmethod
    def get_secret(self, secret_name):
        pass


class FileSecrets(BaseSecretManager):
    """Handler for secrets stored into a file.

    Following environment variables should exist:

        - RPA_SECRET_FILE : filepath to JSON secrets file
    """

    def __init__(self, secret_file="secrets.json"):
        super().__init__()
        if isinstance(secret_file, tuple):
            secret_file = " ".join(secret_file)
        self.secret_file = os.getenv("RPA_SECRET_FILE", secret_file)
        self.secrets = {}
        # make checks for the path
        with open(self.secret_file) as f:
            self.secrets = json.load(f)

    def get_secret(self, secret_name):
        """Get secret defined with key `secret_name` and return
        value of the key.

        If key does not exist raises `KeyError`.

        :param secret_name: secret to fetch
        :return: value of the `secret_name` key or `None`
        """
        secrets = self.secrets[secret_name] if secret_name in self.secrets else None
        if secrets is None:
            raise KeyError(f"Undefined secret: {secret_name}")
        return secrets


class RobocloudVault(BaseSecretManager):
    """Handler for secrets stored into Robocloud SecretsManager.

    Following environment variables should exist:

        - RC_API_SECRET_HOST : URL to Robocloud Secrets API
        - RC_API_SECRET_TOKEN : API Token for Robocloud Secrets API
        - RC_WORKSPACE_ID : Robocloud Workspace ID

    """

    def __init__(self, *_):
        self.secret_host = os.getenv("RC_API_SECRET_HOST", None)
        self.secret_token = os.getenv("RC_API_SECRET_TOKEN", None)
        self.workspace_id = os.getenv("RC_WORKSPACE_ID", None)
        self.headers = {"Authorization": f"Bearer {self.secret_token}"}

    def _get_secret_from_robocloud(self, secret_name):
        try:
            request_url = (
                f"{self.secret_host}/secrets-v1/workspaces/"
                f"{self.workspace_id}/secrets/{secret_name}"
            )
            response = requests.get(request_url, headers=self.headers)
            # If the response was successful, no Exception will be raised
            response.raise_for_status()
            return response.json().get("value", None)
        except Exception:
            raise RobocloudVaultError(
                f"Unable to get secret {secret_name} from RobocloudVault."
            )

    def get_secret(self, secret_name):
        """Get secret defined with key `secret_name` and return
        value of the key.

        If key does not exist raises `KeyError`.

        :param secret_name: secret to fetch
        :return: value of the `secret_name` key or `None`
        """
        secrets = self._get_secret_from_robocloud(secret_name)
        response_as_json = json.loads(secrets) if secrets else None
        if response_as_json is None:
            raise KeyError(f"Undefined secret: {secret_name}")
        return response_as_json
