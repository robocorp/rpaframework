import base64
import binascii
import collections
import copy
import json
import logging
import os
import traceback
from abc import abstractmethod, ABCMeta
from typing import Tuple

import requests
import yaml
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from robot.libraries.BuiltIn import BuiltIn, RobotNotRunningError

from RPA.core.helpers import import_by_name, required_env
from .utils import url_join, resolve_path


class RobocorpVaultError(RuntimeError):
    """Raised when there's problem with reading from Robocorp Vault."""


class Secret(collections.abc.Mapping):
    """Container for a secret with name, description, and
    multiple key-value pairs. Immutable and avoids logging
    internal values when possible.

    :param name:        Name of secret
    :param description: Human-friendly description for secret
    :param values:      Dictionary of key-value pairs stored in secret
    """

    def __init__(self, name, description, values):
        self._name = name
        self._desc = description
        self._dict = collections.OrderedDict(**values)

    @property
    def name(self):
        return self._name

    @property
    def description(self):
        return self._desc

    def update(self, kvpairs):
        self._dict.update(kvpairs)

    def __getitem__(self, key):
        return self._dict[key]

    def __setitem__(self, key, value):
        self._dict[key] = value

    def __contains__(self, key):
        return key in self._dict

    def __iter__(self):
        return iter(self._dict)

    def __len__(self):
        return len(self._dict)

    def __repr__(self):
        return "Secret(name={name}, keys=[{keys}])".format(
            name=self.name, keys=", ".join(str(key) for key in self.keys())
        )


class BaseSecretManager(metaclass=ABCMeta):
    """Abstract class for secrets management. Should be used as a
    base-class for any adapter implementation.
    """

    @abstractmethod
    def get_secret(self, secret_name):
        """Return ``Secret`` object with given name."""

    @abstractmethod
    def set_secret(self, secret: Secret):
        """Set a secret with a new value."""


class FileSecrets(BaseSecretManager):
    """Adapter for secrets stored in a database file. Supports only
    plaintext secrets, and should be used mainly for debugging.

    The path to the secrets file can be set with the
    environment variable ``RPA_SECRET_FILE``, or as
    an argument to the library.

    The format of the secrets file should be one of the following:

    .. code-block:: JSON

      {
        "name1": {
          "key1": "value1",
          "key2": "value2"
        },
        "name2": {
          "key1": "value1"
        }
      }

    OR

    .. code-block:: YAML

      name1:
        key1: value1
        key2: value2
      name2:
        key1: value1
    """

    SERIALIZERS = {
        ".json": (json.load, json.dump),
        ".yaml": (yaml.full_load, yaml.dump),
    }

    def __init__(self, secret_file="secrets.json"):
        self.logger = logging.getLogger(__name__)

        path = required_env("RPA_SECRET_FILE", secret_file)
        self.logger.info("Resolving path: %s", path)
        self.path = resolve_path(path)

        extension = self.path.suffix
        serializer = self.SERIALIZERS.get(extension)
        # NOTE(cmin764): This will raise instead of returning an empty secrets object
        #  because it is wrong starting from the "env.json" configuration level.
        if not serializer:
            raise ValueError(
                f"Not supported local vault secrets file extension {extension!r}"
            )
        self._loader, self._dumper = serializer

        self.data = self.load()

    def load(self):
        """Load secrets file."""
        try:
            with open(self.path, encoding="utf-8") as fd:
                data = self._loader(fd)

            if not isinstance(data, dict):
                raise ValueError("Invalid content format")

            return data
        except (IOError, ValueError) as err:
            self.logger.error("Failed to load secrets file: %s", err)
            return {}

    def save(self):
        """Save the secrets content to disk."""
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                if not isinstance(self.data, dict):
                    raise ValueError("Invalid content format")
                self._dumper(self.data, f, indent=4)
        except (IOError, ValueError) as err:
            self.logger.error("Failed to save secrets file: %s", err)

    def get_secret(self, secret_name):
        """Get secret defined with given name from file.

        :param secret_name: Name of secret to fetch
        :returns:           Secret object
        :raises KeyError:   No secret with given name
        """
        values = self.data.get(secret_name)
        if values is None:
            raise KeyError(f"Undefined secret: {secret_name}")

        return Secret(secret_name, "", values)

    def set_secret(self, secret: Secret) -> None:
        """Set the secret value in the local Vault
        with the given ``Secret`` object.

        :param secret:                 A ``Secret`` object.
        :raises IOError, ValueError:   Writing the local vault failed.
        """
        self.data[secret.name] = dict(secret)
        self.save()


class RobocorpVault(BaseSecretManager):
    """Adapter for secrets stored in Robocorp Vault.

    The following environment variables should exist:

    - RC_API_SECRET_HOST:   URL to Robocorp Secrets API
    - RC_API_SECRET_TOKEN:  API token with access to Robocorp Secrets API
    - RC_WORKSPACE_ID:      Robocorp Workspace ID

    If the robot run is started from the Robocorp Control Room these environment
    variables will be configured automatically.
    """

    ENCRYPTION_SCHEME = "robocloud-vault-transit-v2"

    def __init__(self, *args, **kwargs):
        # pylint: disable=unused-argument
        self.logger = logging.getLogger(__name__)
        # Environment variables set by runner
        self._host = required_env("RC_API_SECRET_HOST")
        self._token = required_env("RC_API_SECRET_TOKEN")
        self._workspace = required_env("RC_WORKSPACE_ID")
        # Generated lazily on request
        self.__private_key = None
        self.__public_bytes = None

    @property
    def headers(self):
        """Default request headers."""
        return {"Authorization": f"Bearer {self._token}"}

    @property
    def params(self):
        """Default request parameters."""
        return {
            "encryptionScheme": self.ENCRYPTION_SCHEME,
            "publicKey": self._public_bytes,
        }

    @property
    def _private_key(self):
        """Cryptography private key object."""
        if self.__private_key is None:
            self.__private_key = rsa.generate_private_key(
                public_exponent=65537, key_size=4096, backend=default_backend()
            )

        return self.__private_key

    @property
    def _public_bytes(self):
        """Serialized public key bytes."""
        if self.__public_bytes is None:
            self.__public_bytes = base64.b64encode(
                self._private_key.public_key().public_bytes(
                    encoding=serialization.Encoding.DER,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo,
                )
            )

        return self.__public_bytes

    def create_secret_url(self, name):
        """Create a URL for a specific secret."""
        return url_join(
            self._host, "secrets-v1", "workspaces", self._workspace, "secrets", name
        )

    def create_public_key_url(self):
        """Create a URL for encryption public key."""
        return url_join(
            self._host,
            "secrets-v1",
            "workspaces",
            self._workspace,
            "secrets",
            "publicKey",
        )

    def get_secret(self, secret_name):
        """Get secret defined with given name from Robocorp Vault.

        :param secret_name:         Name of secret to fetch
        :returns:                   Secret object
        :raises RobocorpVaultError: Error with API request or response payload
        """
        url = self.create_secret_url(secret_name)

        try:
            response = requests.get(url, headers=self.headers, params=self.params)
            response.raise_for_status()

            payload = response.json()
            payload = self._decrypt_payload(payload)
        except InvalidTag as e:
            self.logger.debug(traceback.format_exc())
            raise RobocorpVaultError("Failed to validate authentication tag") from e
        except Exception as exc:
            self.logger.debug(traceback.format_exc())
            raise RobocorpVaultError from exc

        return Secret(payload["name"], payload["description"], payload["values"])

    def _decrypt_payload(self, payload):
        payload = copy.deepcopy(payload)

        fields = payload.pop("encryption", None)
        if fields is None:
            raise KeyError("Missing encryption fields from response")

        scheme = fields["encryptionScheme"]
        if scheme != self.ENCRYPTION_SCHEME:
            raise ValueError(f"Unexpected encryption scheme: {scheme}")

        aes_enc = base64.b64decode(fields["encryptedAES"])
        aes_tag = base64.b64decode(fields["authTag"])
        aes_iv = base64.b64decode(fields["iv"])

        # Decrypt AES key using our private key
        aes_key = self._private_key.decrypt(
            aes_enc,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )

        # Decrypt actual value using decrypted AES key
        ciphertext = base64.b64decode(payload.pop("value")) + aes_tag
        data = AESGCM(aes_key).decrypt(binascii.hexlify(aes_iv), ciphertext, b"")
        payload["values"] = json.loads(data)

        return payload

    def set_secret(self, secret: Secret) -> None:
        """Set the secret value in the Vault. Note that the secret possibly
        consists of multiple key-value pairs, which will all be overwritten
        with the values given here. So don't try to update only one item
        of the secret, update all of them.

        :param secret: A ``Secret`` object
        """
        value, aes_iv, aes_key, aes_tag = self._encrypt_secret_value_with_aes(secret)
        pub_key = self.get_publickey()
        aes_enc = self._encrypt_aes_key_with_public_rsa(aes_key, pub_key)

        payload = {
            "description": secret.description,
            "encryption": {
                "authTag": aes_tag.decode(),
                "encryptedAES": aes_enc.decode(),
                "encryptionScheme": self.ENCRYPTION_SCHEME,
                "iv": aes_iv.decode(),
            },
            "name": secret.name,
            "value": value.decode(),
        }

        url = self.create_secret_url(secret.name)
        try:
            response = requests.put(url, headers=self.headers, json=payload)
            response.raise_for_status()
        except Exception as e:
            self.logger.debug(traceback.format_exc())
            if response.status_code == 403:
                raise RobocorpVaultError(
                    "Failed to set secret value. Does your token have write access?"
                ) from e
            raise RobocorpVaultError("Failed to set secret value.") from e

    def get_publickey(self) -> bytes:
        """Get the public key for AES encryption with the existing token."""
        url = self.create_public_key_url()
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
        except Exception as e:
            self.logger.debug(traceback.format_exc())
            raise RobocorpVaultError(
                "Failed to fetch public key. Is your token valid?"
            ) from e

        return response.content

    @staticmethod
    def _encrypt_secret_value_with_aes(
        secret: Secret,
    ) -> Tuple[bytes, bytes, bytes, bytes]:
        def generate_aes_key() -> Tuple[bytes, bytes]:
            aes_key = AESGCM.generate_key(bit_length=256)
            aes_iv = os.urandom(16)
            return aes_key, aes_iv

        def split_auth_tag_from_encrypted_value(
            encrypted_value: bytes,
        ) -> Tuple[bytes, bytes]:
            """AES auth tag is the last 16 bytes of the AES encrypted value.
            Split the tag from the value, as that is required for the API.
            """
            aes_tag = encrypted_value[-16:]
            trimmed_encrypted_value = encrypted_value[:-16]
            return trimmed_encrypted_value, aes_tag

        value = json.dumps(dict(secret)).encode()

        aes_key, aes_iv = generate_aes_key()
        encrypted_value = AESGCM(aes_key).encrypt(aes_iv, value, b"")
        encrypted_value, aes_tag = split_auth_tag_from_encrypted_value(encrypted_value)

        return (
            base64.b64encode(encrypted_value),
            base64.b64encode(aes_iv),
            aes_key,
            base64.b64encode(aes_tag),
        )

    @staticmethod
    def _encrypt_aes_key_with_public_rsa(aes_key: bytes, public_rsa: bytes) -> bytes:
        pub_decoded = base64.b64decode(public_rsa)
        public_key = serialization.load_der_public_key(pub_decoded)

        aes_enc = public_key.encrypt(
            aes_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )

        return base64.b64encode(aes_enc)


class Vault:
    """`Vault` is a library for interacting with secrets stored in the `Robocorp
    Control Room Vault`_ (by default) or file-based secrets, which can be taken
    into use by setting some environment variables.

    Robocorp Vault relies on environment variables, which are normally set
    automatically by the Robocorp Work Agent or Assistant when a run is
    initialized by the Robocorp Control Room. When developing robots locally
    in VSCode, you can use the `Robocorp Code Extension`_ to set these
    variables automatically as well.

    Alternatively, you may set these environment variable manually using
    `rcc`_ or directly in some other fashion. The specific variables which
    must exist are:

    - ``RC_API_SECRET_HOST``: URL to Robocorp Vault API
    - ``RC_API_SECRET_TOKEN``: API Token for Robocorp Vault API
    - ``RC_WORKSPACE_ID``: Control Room Workspace ID

    .. _Robocorp Control Room Vault: https://robocorp.com/docs/development-guide/variables-and-secrets/vault
    .. _Robocorp Code Extension: https://robocorp.com/docs/developer-tools/visual-studio-code/extension-features#connecting-to-control-room-vault
    .. _rcc: https://robocorp.com/docs/rcc/workflow

    File-based secrets can be set by defining two environment variables.

    - ``RPA_SECRET_MANAGER``: RPA.Robocorp.Vault.FileSecrets
    - ``RPA_SECRET_FILE``: Absolute path to the secrets database file

    Example content of local secrets file:

    .. code-block:: json

        {
            "swaglabs": {
                "username": "standard_user",
                "password": "secret_sauce"
            }
        }

    OR

    .. code-block:: YAML

        swaglabs:
            username: standard_user
            password: secret_sauce

    **Examples of Using Secrets in a Robot**

    **Robot Framework**

    .. code-block:: robotframework

        *** Settings ***
        Library    Collections
        Library    RPA.Robocorp.Vault

        *** Tasks ***
        Reading secrets
            ${secret}=    Get Secret  swaglabs
            Log Many      ${secret}

        Modifying secrets
            ${secret}=          Get Secret      swaglabs
            ${level}=           Set Log Level   NONE
            Set To Dictionary   ${secret}       username    nobody
            Set Log Level       ${level}
            Set Secret          ${secret}


    **Python**

    .. code-block:: python

        from RPA.Robocorp.Vault import Vault

        VAULT = Vault()

        def reading_secrets():
            print(f"My secrets: {VAULT.get_secret('swaglabs')}")

        def modifying_secrets():
            secret = VAULT.get_secret("swaglabs")
            secret["username"] = "nobody"
            VAULT.set_secret(secret)

    """  # noqa: E501

    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    ROBOT_LIBRARY_DOC_FORMAT = "REST"

    def __init__(self, *args, **kwargs):
        """The selected adapter can be set with the environment variable
        ``RPA_SECRET_MANAGER``, or the keyword argument ``default_adapter``.
        Defaults to Robocorp Vault if not defined.

        All other library arguments are passed to the adapter.

        :param default_adapter: Override default secret adapter
        """
        self.logger = logging.getLogger(__name__)

        default = kwargs.pop("default_adapter", RobocorpVault)
        adapter = required_env("RPA_SECRET_MANAGER", default)

        self._adapter_factory = self._create_factory(adapter, args, kwargs)
        self._adapter = None

        try:
            BuiltIn().import_library("RPA.RobotLogListener")
        except RobotNotRunningError:
            pass

    @property
    def adapter(self):
        if self._adapter is None:
            self._adapter = self._adapter_factory()

        return self._adapter

    def _create_factory(self, adapter, args, kwargs):
        if isinstance(adapter, str):
            adapter = import_by_name(adapter, __name__)

        if not issubclass(adapter, BaseSecretManager):
            raise ValueError(
                f"Adapter '{adapter}' does not inherit from BaseSecretManager"
            )

        def factory():
            return adapter(*args, **kwargs)

        return factory

    def get_secret(self, secret_name: str) -> Secret:
        """Read a secret from the configured source, e.g. Robocorp Vault,
        and return it as a ``Secret`` object.

        :param secret_name: Name of secret
        """
        return self.adapter.get_secret(secret_name)

    def set_secret(self, secret: Secret) -> None:
        """Overwrite an existing secret with new values.

        Note: Only allows modifying existing secrets, and replaces
              all values contained within it.

        :param secret: Secret as a ``Secret`` object, from e.g. ``Get Secret``
        """
        self.adapter.set_secret(secret)
