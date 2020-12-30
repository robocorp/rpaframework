import base64
import contextlib
import os
import tempfile
from contextlib import contextmanager

import mock
import pytest
from RPA.Crypto import Crypto, Hash
from RPA.Robocloud.Secrets import Secret


@contextmanager
def temp_path(content=None, suffix=None):
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp:
        path = temp.name
        if content:
            temp.write(content)
    try:
        yield path
    finally:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(path)


def test_generate_key():
    key = Crypto().generate_key()
    assert isinstance(key, str)
    assert len(key) > 0

    keys = [Crypto().generate_key() for _ in range(50)]
    assert len(set(keys)) == len(keys)


def test_set_key():
    lib = Crypto()
    assert lib._key is None

    key = lib.generate_key()
    assert lib._key is None

    lib.use_encryption_key(key)
    assert lib._key is not None

    with pytest.raises(ValueError):
        lib.use_encryption_key("somethingelse")


def test_hash_string():
    result = Crypto().hash_string("avalue")
    assert result == "eNOTzEOqI0k2ijVhEmKow1YPFGo="


def test_hash_string_unicode():
    result = Crypto().hash_string("谷歌翻译是你的朋友")
    assert result == "J5TSpa76g8qV1pws6H6ztDEfYeo="


def test_hash_string_method():
    result = Crypto().hash_string("avalue", method=Hash.MD5)
    assert result == "3ObaKiohbtSuG4Q8+kIKTg=="


def test_hash_file():
    with temp_path("avalue".encode("utf-8")) as infile:
        result = Crypto().hash_file(infile)
        assert result == "eNOTzEOqI0k2ijVhEmKow1YPFGo="


def test_encrypt_decrypt_string():
    lib = Crypto()

    key = lib.generate_key()
    lib.use_encryption_key(key)

    text = "An example string\nWith some secret content"
    encrypted = lib.encrypt_string(text)

    assert encrypted != text
    assert base64.urlsafe_b64decode(encrypted) != text

    decrypted = lib.decrypt_string(encrypted)
    assert decrypted == text


def test_decrypt_wrong_key():
    lib = Crypto()

    key1 = lib.generate_key()
    key2 = lib.generate_key()
    assert key1 != key2

    lib.use_encryption_key(key1)
    text = "An example string\nWith some secret content"
    token = lib.encrypt_string(text)

    lib.use_encryption_key(key2)
    with pytest.raises(ValueError):
        lib.decrypt_string(token)


def test_encrypt_decrypt_file():
    lib = Crypto()

    key = lib.generate_key()
    lib.use_encryption_key(key)

    text = "An example string\nWith some secret content"

    with temp_path() as encrypted:
        with temp_path(text.encode("utf-8")) as original:
            result = lib.encrypt_file(original, encrypted)
            assert result == encrypted
            assert os.stat(result).st_size > 0

        with temp_path() as decrypted:
            result = lib.decrypt_file(encrypted, decrypted)
            assert result == decrypted
            with open(result) as resultfile:
                assert resultfile.read() == text


def test_encrypt_file_default_paths():
    lib = Crypto()

    key = lib.generate_key()
    lib.use_encryption_key(key)

    text = "An example string\nWith some secret content"

    with temp_path(text.encode("utf-8")) as original:
        encrypted, decrypted = "", ""
        try:
            encrypted = lib.encrypt_file(original)
            assert encrypted == original + ".enc"

            decrypted = lib.decrypt_file(encrypted)
            assert decrypted == original
        finally:
            with contextlib.suppress(FileNotFoundError):
                os.unlink(encrypted)
                os.unlink(decrypted)


def test_encrypt_file_suffix():
    lib = Crypto()

    key = lib.generate_key()
    lib.use_encryption_key(key)

    text = "An example string\nWith some secret content"

    with temp_path(text.encode("utf-8")) as original:
        with temp_path(suffix=".bin") as encrypted:
            lib.encrypt_file(original, encrypted)
            result = lib.decrypt_file(encrypted)
            try:
                assert os.path.isfile(result)
                assert result.endswith(".dec.bin")
            finally:
                with contextlib.suppress(FileNotFoundError):
                    os.unlink(result)


def test_set_key_vault_no_key():
    lib = Crypto()
    lib._secrets = mock_secrets = mock.Mock()

    key = lib.generate_key()
    mock_secrets.get_secret.return_value = Secret("MockSecret", "", {"key": key})

    lib.use_encryption_key_from_vault("SomeKeyValue")
    assert mock_secrets.get_secret.called_once_with("SomeKeyValue")
    assert lib._key is not None


def test_set_key_vault_key():
    lib = Crypto()
    lib._secrets = mock_secrets = mock.Mock()

    key = lib.generate_key()
    mock_secrets.get_secret.return_value = Secret(
        "MockSecret", "", {"first": "something", "second": key}
    )

    lib.use_encryption_key_from_vault("SomeKeyValue", "second")
    assert mock_secrets.get_secret.called_once_with("SomeKeyValue")
    assert lib._key is not None


def test_set_key_vault_error_multiple():
    lib = Crypto()
    lib._secrets = mock_secrets = mock.Mock()

    key = lib.generate_key()
    mock_secrets.get_secret.return_value = Secret(
        "MockSecret", "", {"first": "something", "second": key}
    )

    with pytest.raises(ValueError):
        lib.use_encryption_key_from_vault("SomeKeyValue")
    assert mock_secrets.get_secret.called_once_with("SomeKeyValue")
    assert lib._key is None


def test_set_key_vault_error_empty():
    lib = Crypto()
    lib._secrets = mock_secrets = mock.Mock()

    key = lib.generate_key()
    mock_secrets.get_secret.return_value = Secret("MockSecret", "", {})

    with pytest.raises(ValueError):
        lib.use_encryption_key_from_vault("SomeKeyValue")
    assert mock_secrets.get_secret.called_once_with("SomeKeyValue")
    assert lib._key is None
