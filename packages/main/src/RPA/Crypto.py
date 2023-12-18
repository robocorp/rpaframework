import base64
from enum import Enum, auto
from pathlib import Path
from secrets import token_bytes
from typing import Optional, Union

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from robot.libraries.BuiltIn import BuiltIn, RobotNotRunningError

from RPA.RobotLogListener import RobotLogListener
from RPA.Robocorp.Vault import Vault

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


class EncryptionType(Enum):
    """Enum to specify encryption type"""

    FERNET = auto()
    AES256 = auto()


def to_encryption_type(value, default_value):
    """Convert value to EncryptionType enum."""
    if not value:
        return default_value

    if isinstance(value, EncryptionType):
        return value

    sanitized = str(value).upper().strip().replace(" ", "_")
    try:
        return EncryptionType[sanitized]
    except KeyError as err:
        raise ValueError(f"Unknown EncryptionType: {value}") from err


class UnknownEncryptionTypeError(Exception):
    """Raised when unknown encryption type is used."""


def to_hash_context(element: Hash) -> hashes.HashContext:
    """Convert hash enum value to hash context instance."""
    method = getattr(hashes, str(element.name))
    return hashes.Hash(method(), backend=default_backend())


class Crypto:
    """Library for common encryption and hashing operations.

    Library uses by default the
    `Fernet <https://github.com/fernet/spec/blob/master/Spec.md>`_ format
    for encryption. More specifically, it uses AES in CBC mode with
    a 128-bit key for encryption and HMAC with SHA256 for authentication.

    Alternative encryption format for the library is
    `AES256 <https://en.wikipedia.org/wiki/Advanced_Encryption_Standard>`_.

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

    def __init__(self, encryption_type: Optional[Union[str, EncryptionType]] = None):
        self._vault = Vault()
        self._key = None
        self._encryption_method = to_encryption_type(
            encryption_type, EncryptionType.FERNET
        )
        listener = RobotLogListener()
        listener.register_protected_keywords(
            ["RPA.Crypto.generate_key", "RPA.Crypto.use_encryption_key"]
        )

    def generate_key(
        self, encryption_type: Optional[Union[str, EncryptionType]] = None
    ) -> str:
        """Generate a Fernet encryption key as base64 string.

        :return: Generated key as a string

        This key can be used for encryption/decryption operations
        with this library.

        *NOTE:* Store the generated key in a secure place!
        If the key is lost, the encrypted data can not be recovered.
        If anyone else gains access to it, they can decrypt your data.
        """
        encryption_type = to_encryption_type(encryption_type, self._encryption_method)
        if encryption_type == EncryptionType.FERNET:
            return Fernet.generate_key().decode("utf-8")
        elif encryption_type == EncryptionType.AES256:
            return self._generate_aes256_key().decode("utf-8")
        else:
            raise UnknownEncryptionTypeError

    def use_encryption_key(
        self,
        key: Union[bytes, str],
        encryption_type: Optional[Union[str, EncryptionType]] = None,
    ) -> None:
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
        encryption_type = to_encryption_type(encryption_type, self._encryption_method)
        if encryption_type == EncryptionType.FERNET:
            self._key = Fernet(key)
        elif encryption_type == EncryptionType.AES256:
            self._key = key
        else:
            raise UnknownEncryptionTypeError
        self._encryption_method = encryption_type

    def use_encryption_key_from_vault(
        self,
        name: str,
        key: Optional[str] = None,
        encryption_type: Optional[Union[str, EncryptionType]] = None,
    ) -> None:
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
        encryption_type = to_encryption_type(encryption_type, self._encryption_method)
        secret = self._vault.get_secret(name)

        if key:
            value = secret[key]
        elif len(secret) == 1:
            value = list(secret.values())[0]
        elif len(secret) == 0:
            raise ValueError(f"Secret '{name}' has no values")
        else:
            options = ", ".join(str(k) for k in secret.keys())
            raise ValueError(f"Secret '{name}' has multiple values: {options}")

        self.use_encryption_key(value, encryption_type=encryption_type)

    def hash_string(self, text: str, method: Hash = Hash.SHA1, encoding="utf-8") -> str:
        """Calculate a hash from a string, in base64 format.

        :param text: String to hash
        :param method: Used hashing method
        :param encoding: Used text encoding
        :return: Hash digest of the string

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
        :return: Hash digest of the file

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

    def encrypt_string(
        self,
        text: Union[bytes, str],
        encoding: str = "utf-8",
        encryption_type: Optional[Union[str, EncryptionType]] = None,
    ) -> bytes:
        """Encrypt a string.

        :param text: Source text to encrypt
        :param encoding: Used text encoding
        :return: Token of the encrypted string in bytes

        Example:

        .. code-block:: robotframework

            Use encryption key    ${key}
            ${token}=    Encrypt string    This is a secret, don't share it
        """
        if not self._key:
            raise ValueError("No encryption key set")

        if isinstance(text, str):
            text = text.encode(encoding)

        encryption_type = to_encryption_type(encryption_type, self._encryption_method)

        if encryption_type == EncryptionType.FERNET:
            return self._key.encrypt(text)
        elif encryption_type == EncryptionType.AES256:
            return self._encrypt_aes256(text)
        else:
            raise UnknownEncryptionTypeError

    def decrypt_string(
        self,
        data: Union[bytes, str],
        encoding: str = "utf-8",
        encryption_type: Optional[Union[str, EncryptionType]] = None,
    ) -> Union[str, bytes]:
        """Decrypt a string.

        :param data: Encrypted data as base64 string
        :param encoding: Original encoding of string
        :return: Decrypted string or raw bytes, if None given as encoding

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

        encryption_type = to_encryption_type(encryption_type, self._encryption_method)

        if encryption_type == EncryptionType.FERNET:
            try:
                text = self._key.decrypt(data)
            except InvalidToken as err:
                raise ValueError(
                    "Failed to decrypt string (malformed content or invalid signature)"
                ) from err
            except AttributeError as err:
                raise ValueError(
                    "Failed to decrypt string as Fernet encryption type "
                    "(invalid key or key type)"
                ) from err

            if encoding is not None:
                text = text.decode(encoding)
            return text
        elif encryption_type == EncryptionType.AES256:
            text = self._decrypt_aes256(data)
            if encoding is not None:
                text = text.decode(encoding)
            return text
        else:
            raise UnknownEncryptionTypeError

    def encrypt_file(
        self,
        path: str,
        output: Optional[str] = None,
        encryption_type: Optional[Union[str, EncryptionType]] = None,
    ) -> str:
        """Encrypt a file.

        :param path: Path to source input file
        :param output: Path to encrypted output file
        :return: Path to the encrypted file

        If no output path is given, it will generate one from the input path.
        The resulting output path is returned.

        Example:

        .. code-block:: robotframework

            Use encryption key    ${key}
            ${path}=    Encrypt file    orders.xlsx
            Log    Path to encrypted file is: ${path}
        """
        encryption_type = to_encryption_type(encryption_type, self._encryption_method)

        path = Path(path)
        if not self._key:
            raise ValueError("No encryption key set")

        if output:
            output = Path(output)
        else:
            output = path.parent / (path.name + ".enc")

        with open(path, "rb") as infile:
            data = infile.read()
            if encryption_type == EncryptionType.FERNET:
                token = self._key.encrypt(data)
            elif encryption_type == EncryptionType.AES256:
                token = self._encrypt_aes256(data)

        with open(output, "wb") as outfile:
            outfile.write(token)
            return str(output)

    def decrypt_file(
        self,
        path: str,
        output: Optional[str] = None,
        encryption_type: Optional[Union[str, EncryptionType]] = None,
    ) -> str:
        """Decrypt a file.

        :param path: Path to encrypted input file
        :param output: Path to decrypted output file
        :return: Path to the decrypted file

        If no output path is given, it will generate one from the input path.
        The resulting output path is returned.

        Example:

        .. code-block:: robotframework

            Use encryption key    ${key}
            ${path}=    Decrypt file    orders.xlsx.enc
            Log    Path to decrypted file is: ${path}
        """
        encryption_type = to_encryption_type(encryption_type, self._encryption_method)

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
                if encryption_type == EncryptionType.FERNET:
                    data = self._key.decrypt(token)
                elif encryption_type == EncryptionType.AES256:
                    data = self._decrypt_aes256(token)
        except InvalidToken as err:
            raise ValueError(
                "Failed to decrypt file (malformed content or invalid signature)"
            ) from err

        with open(output, "wb") as outfile:
            outfile.write(data)
            return str(output)

    # Helper methods for AES256 (same as before)
    def _generate_aes256_key(self) -> bytes:
        key = token_bytes(32)
        return base64.urlsafe_b64encode(key)

    def _encrypt_aes256(self, data: bytes) -> bytes:
        backend = default_backend()
        iv = token_bytes(12)
        cipher = Cipher(
            algorithms.AES(base64.urlsafe_b64decode(self._key)),
            modes.GCM(iv),
            backend=backend,
        )
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(data) + encryptor.finalize()
        return iv + encryptor.tag + ciphertext

    def _decrypt_aes256(self, data: bytes) -> bytes:
        backend = default_backend()
        iv = data[:12]
        tag = data[12:28]
        ciphertext = data[28:]
        cipher = Cipher(
            algorithms.AES(base64.urlsafe_b64decode(self._key)),
            modes.GCM(iv, tag),
            backend=backend,
        )
        decryptor = cipher.decryptor()
        return decryptor.update(ciphertext) + decryptor.finalize()
