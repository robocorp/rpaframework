import pytest


class Trollo(object):
    def __init__(self):
        pass


def test_use_secret_manager_when_environment_is_not_set(monkeypatch):
    monkeypatch.delenv("RPA_SECRET_MANAGER", raising=False)
    from RPA.Robocloud.Secrets import Secrets

    sm = Secrets()
    assert sm.secretmanager == "RPA.Robocloud.Secrets.RobocloudVault"


def test_file_secret_manager(monkeypatch):
    monkeypatch.setenv("RPA_SECRET_MANAGER", "RPA.Robocloud.Secrets.FileSecrets")
    monkeypatch.setenv("RPA_SECRET_FILE", "tests/resources/secrets.json")
    from RPA.Robocloud.Secrets import Secrets

    sm = Secrets()
    assert sm.secretmanager == "RPA.Robocloud.Secrets.FileSecrets"
    secrets = sm.get_secret("credentials")
    assert secrets["sap"]["login"] == "robot"
    assert secrets["sap"]["password"] == "secret"
    assert secrets["google"]["apikey"] == "1234567890"


def test_not_existing_class_as_secret_manager(monkeypatch):
    monkeypatch.setenv("RPA_SECRET_MANAGER", "RPA.NotExistingSecretManager")
    from RPA.Robocloud.Secrets import Secrets

    with pytest.raises(Exception):
        Secrets()


def test_invalid_base_class_as_secret_manager(monkeypatch):
    monkeypatch.setenv("RPA_SECRET_MANAGER", "RPA.Trollo")
    from RPA.Robocloud.Secrets import Secrets

    with pytest.raises(Exception):
        Secrets()


def test_direct_instance_of_robocloud_vault():
    from RPA.Robocloud.Secrets import RobocloudVault

    sm = RobocloudVault()
    assert sm.headers is not None


def test_error_with_robocloud_vault_when_no_configuration_exists():
    from RPA.Robocloud.Secrets import RobocloudVault, RobocloudVaultError

    sm = RobocloudVault()
    with pytest.raises(RobocloudVaultError):
        sm.get_secret("myspecialsecret")


def test_direct_instance_of_file_secret_manager(monkeypatch):
    monkeypatch.setenv("RPA_SECRET_FILE", "tests/resources/secrets.json")
    from RPA.Robocloud.Secrets import FileSecrets

    sm = FileSecrets()
    secrets_windows = sm.get_secret("windows")
    secrets_robocloud = sm.get_secret("robocloud")
    assert secrets_windows["domain"] == "windows"
    assert secrets_windows["login"] == "robot"
    assert secrets_windows["password"] == "secret"
    assert secrets_robocloud["url"] == "http://robocloud.ai/"
    assert secrets_robocloud["login"] == "robot"
    assert secrets_robocloud["password"] == "secret"
