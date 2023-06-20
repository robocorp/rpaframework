from typing import List

from robocorp import storage
from robot.api.deco import keyword, library


@library
class Storage:
    """Control Room `Storage Asset` library operating with the built-in cloud key-value
    store.
    """

    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    ROBOT_LIBRARY_DOC_FORMAT = "REST"

    @keyword
    def list_assets(self) -> List[storage.AssetMeta]:
        return storage.list_assets()

    @keyword
    def get_asset(self, name: str) -> str:
        return storage.get_asset(name)

    @keyword
    def set_asset(self, name: str, value: str, wait: bool = True):
        storage.set_asset(name, value, wait=wait)

    @keyword
    def delete_asset(self, name: str):
        storage.delete_asset(name)
