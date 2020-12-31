import base64
from enum import Enum, auto
from pathlib import Path
from typing import Optional, Union

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from robot.libraries.BuiltIn import BuiltIn, RobotNotRunningError

from RPA.RobotLogListener import RobotLogListener
from RPA.Robocloud.Secrets import Secrets

try:
    BuiltIn().import_library("RPA.RobotLogListener")
except RobotNotRunningError:
    pass


class Hash(Enum):
    """Supported hashing algorithms."""

    MD5 = auto()
    SHA1 = auto()
    SHA224 = auto()
    SHA256 = auto()
    SHA384 = auto()
    SHA3_224 = auto()
    SHA3_256 = auto()
    SHA3_384 = auto()
    SHA3_512 = auto()
    SHA512 = auto()
    SHA512_224 = auto()
    SHA512_256 = auto()


def to_hash_context(element: Hash) -> hashes.HashContext:
    """Convert hash enum value to hash context instance."""
    method = getattr(hashes, str(element.name))
    return hashes.Hash(method(), backend=default_backend())


class Crypto:
    """Library for common encryption and hashing operations.

    It uses the `Fernet <https://github.com/fernet/spec/blob/master/Spec.md>`_
    format for encryption. More specifically, it uses AES in
    CBC mode with a 128-bit key for encryption and HMAC with SHA256 for
    authentication.

    To use the encryption features, generate a key with the command line
    utility ``rpa-crypto`` or with the keyword ``Generate Key``. Store
    the key in a secure place, such as Robocorp Vault, and load it within
    the execution before calling encryption/decryption keywords.

    **Example usage with Robocorp Vault**

    Create an encryption key with the CLI utility:

    .. code-block:: console

        > rpa-crypto key
        rGx1edA07yz7uD08ChiPSunn8vaauRxw0pAbsal9zjM=

    Store the key in Robocorp Vault, in this case with the name ``EncryptionKey``.

    Load the key from the vault before encryption operations:

    .. code-block:: robotframework

        Use encryption key from vault    EncryptionKey
        ${encrypted}=   Encrypt file    orders.xlsx
        Add work item file    ${encrypted}    name=Orders

    In another task, this same key can be used to decrypt the file:

    .. code-block:: robotframework

        Use encryption key from vault    EncryptionKey
        ${encrypted}=    Get work item file    Orders
        ${orders}=   Decrypt file    ${encrypted}
    """

    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    ROBOT_LIBRARY_DOC_FORMAT = "REST"

    def __init__(self):
        self._secrets = Secrets()
        self._key = None
        listener = RobotLogListener()
        listener.register_protected_keywords(
            ["RPA.Crypto.generate_key", "RPA.Crypto.use_encryption_key"]
        )

    def generate_key(self) -> str:
        """Generate a Fernet encryption key as base64 string.

        This key can be used for encryption/decryption operations
        with this library.

        *NOTE:* Store the generated key in a secure place!
        If the key is lost, the encrypted data can not be recovered.
        If anyone else gains access to it, they can decrypt your data.
        """
        return Fernet.generate_key().decode("utf-8")

    def use_encryption_key(self, key: str):
        """Set key for all following encryption/decryption operations.

        :param key: Encryption key as base64 string

        Assumes the given key has been generated previously using
        either the keyword ``Generate Key`` or with the matching command
        line utility.

        Example:

        .. code-block:: robotframework

            ${key}=    Read file    encryption.key
            Use encryption key      ${key}
        """
        self._key = Fernet(key)

    def use_encryption_key_from_vault(self, name: str, key: Optional[str] = None):
        """Load an encryption key from Robocorp Vault.

        :param name: Name of secret in Vault
        :param key: Name of encryption key in secret

        If the secret only has one value, the key argument is optional.

        Example:

        .. code-block:: robotframework

            # Secret with one value
            Use encryption key from vault    Encryption
            # Secret with multiple values
            Use encryption key from vault    name=Encryption    key=CryptoKey
        """
        secret = self._secrets.get_secret(name)

        if key:
            value = secret[key]
        elif len(secret) == 1:
            value = list(secret.values())[0]
        elif len(secret) == 0:
            raise ValueError(f"Secret '{name}' has no values")
        else:
            options = ", ".join(str(k) for k in secret.keys())
            raise ValueError(f"Secret '{name}' has multiple values: {options}")

        self.use_encryption_key(value)

    def hash_string(self, text: str, method: Hash = Hash.SHA1, encoding="utf-8") -> str:
        """Calculate a hash from a string, in base64 format.

        :param text: String to hash
        :param method: Used hashing method
        :param encoding: Used text encoding

        Example:

        .. code-block:: robotframework

            ${digest}=    Hash string    A value that will be hashed
            Should be equal    ${digest}    uSlyRHlbu8NzY29YMZhDUpdErP4=
        """
        if isinstance(text, str):
            text = text.encode(encoding)

        context = to_hash_context(method)
        context.update(text)

        digest = context.finalize()
        return base64.b64encode(digest).decode("utf-8")

    def hash_file(self, path: str, method: Hash = Hash.SHA1) -> str:
        """Calculate a hash from a file, in base64 format.

        :param path: Path to file
        :param method: The used hashing method

        Example:

        .. code-block:: robotframework

            ${digest}=    Hash file    orders.xlsx    method=MD5
            Should not be equal    ${digest}    uSlyRHlbu8NzY29YMZhDUpdErP4=
        """
        context = to_hash_context(method)
        with open(path, "rb") as infile:
            while True:
                chunk = infile.read(65536)
                if not chunk:
                    break
                context.update(chunk)

        digest = context.finalize()
        return base64.b64encode(digest).decode("utf-8")

    def encrypt_string(self, text: Union[str, bytes], encoding="utf-8") -> bytes:
        """Encrypt a string.

        :param text: Source text to encrypt
        :param encoding: Used text encoding

        Example:

        .. code-block:: robotframework

            Use encryption key    ${key}
            ${token}=    Encrypt string    This is a secret, don't share it
        """
        if not self._key:
            raise ValueError("No encryption key set")

        if isinstance(text, str):
            text = text.encode(encoding)

        token = self._key.encrypt(text)
        return token

    def decrypt_string(
        self, data: Union[str, bytes], encoding="utf-8"
    ) -> Union[str, bytes]:
        """Decrypt a string.

        :param data: Encrypted data as base64 string
        :param encoding: Original encoding of string

        Returns the decrypted string that is parsed with the given encoding,
        or if the encoding is ``None`` the raw bytes are returned.

        Example:

        .. code-block:: robotframework

            Use encryption key    ${key}
            ${text}=    Decrypt string    ${token}
            Log    Secret string is: ${text}
        """
        if not self._key:
            raise ValueError("No encryption key set")

        if isinstance(data, str):
            data = data.encode("utf-8")

        try:
            text = self._key.decrypt(data)
        except InvalidToken as err:
            raise ValueError(
                "Failed to decrypt string (malformed content or invalid signature)"
            ) from err

        if encoding is not None:
            text = text.decode(encoding)

        return text

    def encrypt_file(self, path: str, output: Optional[str] = None) -> str:
        """Encrypt a file.

        :param path: Path to source input file
        :param output: Path to encrypted output file

        If not output path is given, it will generate one from the input path.
        The resulting output path is returned.

        Example:

        .. code-block:: robotframework

            Use encryption key    ${key}
            ${path}=    Encrypt file    orders.xlsx
            Log    Path to encrypted file is: ${path}
        """
        path = Path(path)
        if not self._key:
            raise ValueError("No encryption key set")

        if output:
            output = Path(output)
        else:
            output = path.parent / (path.name + ".enc")

        with open(path, "rb") as infile:
            data = infile.read()
            token = self._key.encrypt(data)

        with open(output, "wb") as outfile:
            outfile.write(token)
            return str(output)

    def decrypt_file(self, path: str, output: Optional[str] = None) -> str:
        """Decrypt a file.

        :param path: Path to encrypted input file
        :param output: Path to decrypted output file

        If not output path is given, it will generate one from the input path.
        The resulting output path is returned.

        Example:

        .. code-block:: robotframework

            Use encryption key    ${key}
            ${path}=    Decrypt file    orders.xlsx.enc
            Log    Path to decrypted file is: ${path}
        """
        path = Path(path)
        if not self._key:
            raise ValueError("No encryption key set")

        if output:
            output = Path(output)
        elif path.name.endswith(".enc"):
            output = path.parent / path.name[: -len(".enc")]
        else:
            parts = (path.stem, "dec", path.suffix[1:])
            output = path.parent / ".".join(part for part in parts if part.strip())

        try:
            with open(path, "rb") as infile:
                token = infile.read()
                data = self._key.decrypt(token)
        except InvalidToken as err:
            raise ValueError(
                "Failed to decrypt file (malformed content or invalid signature)"
            ) from err

        with open(output, "wb") as outfile:
            outfile.write(data)
            return str(output)
