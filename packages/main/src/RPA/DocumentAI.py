"""Generic Intelligent Document Processing generic keywords capable of working with
various engines.

Currently, supporting the following:
- Google Document AI
- Base64
- Nanonets
"""


import functools
import logging
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union

from robot.api.deco import keyword, library

from RPA.JSON import JSONType
from RPA.Robocorp.Vault import Vault


# FIXME: Type annotations globally.

lib_vault = Vault()

SecretType = Optional[Union[str, Path]]


class EngineName(Enum):
    """Supported engines to process documents with."""

    GOOGLE = "google"
    BASE64 = "base64ai"
    NANONETS = "nanonets"


@library
class DocumentAI:
    """<summary>

    <details>
    <engines examples>
    <extra requirements>
    <about models/processors>
    <input and output>
    <service setup>
    """

    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    ROBOT_LIBRARY_DOC_FORMAT = "REST"

    def __init__(self):
        self._engines: Dict[EngineName, Any] = {}
        self._active_engine: Optional[EngineName] = None

    @staticmethod
    def _get_secret_value(secret: Optional[str], vault: Optional[Dict]) -> SecretType:
        if vault:
            assert (
                len(vault) == 1
            ), "`vault` should contain one key (Vault name) and one value (secret key)"
            name, key = list(vault.items())[0]
            secrets = lib_vault.get_secret(name)
            logging.debug("Using secret from the Vault.")
            return secrets[key]

        if not secret:
            logging.debug("Using secret implicitly from environment variable(s).")
            return None

        secret_path = Path(secret).expanduser().resolve()
        if secret_path.exists():
            # File-based secret, don't return its content, but its file location
            #  as object instead. (the engine itself knows how to use it from there)
            logging.debug("Using secret from local file path at: %s", secret_path)
            return secret_path

        logging.debug("Using secret as provided.")
        return secret  # secret in plain text

    def _init_google(
        self,
        secret_value: SecretType,
        vault: Optional[Dict] = None,
        auth_type: Optional[str] = None,
        region: Optional[str] = None,
    ):
        try:
            from RPA.Cloud.Google import Google
        except ImportError as exc:
            raise ImportError(
                "dependency `rpaframework-google` needs to be installed in order to"
                " use the 'google' engine"
            ) from exc

        lib_kwargs = {}
        init_kwargs = {}
        if vault:
            # Vault is enabled, so mark the same in the engine library as well.
            name, key = list(vault.items())[0]
            lib_kwargs.update(
                {
                    "vault_name": name,
                    "vault_secret_key": key,
                }
            )
            init_kwargs["use_robocorp_vault"] = True
        elif secret_value:
            # Vault not used, therefore the provided secret is a file path pointing to
            #  a service account or token JSON file.
            if (auth_type or "serviceaccount") == "serviceaccount":
                secret_type = "service_account"
            else:
                secret_type = "token_file"
            init_kwargs[secret_type] = str(secret_value)
        if auth_type:
            lib_kwargs["cloud_auth_type"] = auth_type
        if region:
            init_kwargs["region"] = region

        engine = Google(**lib_kwargs)
        engine.init_document_ai(**init_kwargs)
        self._engines[EngineName.GOOGLE] = engine

    @staticmethod
    def _secret_value_to_params(secret_value: str) -> Tuple[str]:
        return tuple(part.strip() for part in secret_value.split(","))

    def _init_base64(self, secret_value: SecretType):
        from RPA.Base64AI import Base64AI

        engine = Base64AI()
        engine.set_authorization(*self._secret_value_to_params(secret_value))
        self._engines[EngineName.BASE64] = engine

    def _init_nanonets(self, secret_value: SecretType):
        from RPA.Nanonets import Nanonets

        engine = Nanonets()
        engine.set_authorization(*self._secret_value_to_params(secret_value))
        self._engines[EngineName.NANONETS] = engine

    @keyword
    def switch_engine(self, name: Union[EngineName, str]):
        name: EngineName = (
            name if isinstance(name, EngineName) else EngineName(name.lower())
        )
        if name not in self._engines:
            raise RuntimeError(
                f"can't switch to {name.value!r} engine, please run"
                f" `Init Engine    {name.value}    ...` first"
            )

        self._active_engine = name

    @keyword
    def init_engine(
        self,
        name: Union[EngineName, str],
        secret: Optional[str] = None,
        vault: Optional[Dict] = None,
        **kwargs,
    ):
        """<summary>

        <params>
        <example>
        """
        if secret and vault:
            raise ValueError("choose between `secret` and `vault`")
        elif not (secret or vault):
            logging.warning("No `secret` or `vault` provided, relying on env vars.")

        init_map = {
            # Google library needs to be Vault aware too due to its internal way of
            #  handling secrets from there.
            EngineName.GOOGLE: functools.partial(self._init_google, vault=vault),
            # Rest of the engines have a normalized way of picking up secrets either
            #  provided directly (as string or file path) either through Vault (
            #  dictionary of parameters).
            EngineName.BASE64: self._init_base64,
            EngineName.NANONETS: self._init_nanonets,
        }
        name: EngineName = (
            name if isinstance(name, EngineName) else EngineName(name.lower())
        )
        secret_value = self._get_secret_value(secret, vault)

        # Will raise by itself if additional `kwargs` are required but not provided,
        #  given the selected engine.
        init_map[name](secret_value, **kwargs)
        self.switch_engine(name)

    def _check_engine(self):
        if not self._active_engine:
            raise RuntimeError(
                "can't execute without an engine set, please run"
                " `Init Engine    <name>    ...` first"
            )

    @keyword
    def predict(self, location, model=None, **kwargs):
        """<summary>

        <params>
        <example>
        """
        self._check_engine()
        # TODO: Run adequate prediction keyword.

    @keyword
    def get_result(self) -> JSONType:
        """<summary>

        <example>
        """
        self._check_engine()
        # TODO: Run adequate result retrieval keyword.
        return {}
