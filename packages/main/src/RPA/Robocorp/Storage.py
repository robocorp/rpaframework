from typing import Dict, List

from robocorp import storage
from robot.api.deco import keyword, library


@library
class Storage:
    """Control Room `Asset Storage` library operating with the cloud built-in key-value
    store.

    Library requires at the minimum `rpaframework` version **24.0.0**.

    **Usage**

    .. code-block:: robotframework

        *** Tasks ***
        Manage Assets
            @{assets} =    List Assets
            Log List    ${assets}

            Set Text Asset    my-asset    My string asset value
            ${value} =      Get Text Asset       my-asset
            Log     Asset value: ${value}

            Delete Asset    my-asset

    .. code-block:: python

        import logging
        from RPA.Robocorp.Storage import Storage

        storage = Storage()

        def manage_assets():
            assets = storage.list_assets()
            logging.info(assets)

            storage.set_text_asset("my-asset", "My string asset value")
            value = storage.get_text_asset("my-asset")
            logging.info("Asset value: %s", value)

            storage.delete_asset("my-asset")

    **Caveats**

    Currently, there's no local file adapter support, therefore you need to be linked
    to Control Room and connected to a Workspace in VSCode before being able to develop
    locally robots using this functionality.

    While the content type can be controlled (during bytes and file setting), it is
    currently disabled in this version of the library for simplicity reasons.
    """

    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    ROBOT_LIBRARY_DOC_FORMAT = "REST"

    @keyword
    def list_assets(self) -> List[str]:
        """List all the existing assets.

        :returns: A list of available assets' names

        **Example: Robot Framework**

        .. code-block:: robotframework

            *** Tasks ***
            Print All Assets
                @{assets} =    List Assets
                Log List    ${assets}

        **Example: Python**

        .. code-block:: python

            def print_all_assets():
                print(storage.list_assets())
        """
        return storage.list_assets()

    @keyword
    def set_bytes_asset(self, name: str, value: bytes, wait: bool = True):
        """Creates or updates an asset named `name` with the provided bytes `value`.

        :param name: Name of the existing or new asset to create (if missing)
        :param value: The new bytes value to set within the asset
        :param wait: Wait for the value to be set successfully

        **Example: Robot Framework**

        .. code-block:: robotframework

            *** Tasks ***
            Set An Asset
                ${random_bytes} =      Evaluate    os.urandom(10)      modules=os
                Set Bytes Asset    my-bytes-asset    ${random_bytes}

        **Example: Python**

        .. code-block:: python

            import os

            def set_an_asset():
                random_bytes = os.urandom(10)
                storage.set_bytes_asset("my-bytes-asset", random_bytes)
        """
        storage.set_bytes(name, data=value, wait=wait)

    @keyword
    def get_bytes_asset(self, name: str) -> bytes:
        """Get the asset's bytes value by providing its `name`.

        :param name: Name of the asset
        :raises AssetNotFound: Asset with the given name does not exist
        :returns: The current value of this asset as bytes

        **Example: Robot Framework**

        .. code-block:: robotframework

            *** Tasks ***
            Retrieve An Asset
                ${value} =      Get Bytes Asset       my-bytes-asset
                Log     Asset bytes value: ${value}

        **Example: Python**

        .. code-block:: python

            def retrieve_an_asset():
                value = storage.get_bytes_asset("my-bytes-asset")
                print(b"Asset bytes value:", value)
        """
        return storage.get_bytes(name)

    @keyword
    def set_text_asset(self, name: str, value: str, wait: bool = True):
        """Creates or updates an asset named `name` with the provided text `value`.

        :param name: Name of the existing or new asset to create (if missing)
        :param value: The new text value to set within the asset
        :param wait: Wait for the value to be set successfully

        **Example: Robot Framework**

        .. code-block:: robotframework

            *** Tasks ***
            Set An Asset
                Set Text Asset    my-text-asset    My asset value as text

        **Example: Python**

        .. code-block:: python

            def set_an_asset():
                storage.set_text_asset("my-text-asset", "My asset value as text")
        """
        storage.set_text(name, text=value, wait=wait)

    @keyword
    def get_text_asset(self, name: str) -> str:
        """Get the asset's text value by providing its `name`.

        :param name: Name of the asset
        :raises AssetNotFound: Asset with the given name does not exist
        :returns: The current value of this asset as text

        **Example: Robot Framework**

        .. code-block:: robotframework

            *** Tasks ***
            Retrieve An Asset
                ${value} =      Get Text Asset       my-text-asset
                Log     Asset text value: ${value}

        **Example: Python**

        .. code-block:: python

            def retrieve_an_asset():
                value = storage.get_text_asset("my-text-asset")
                print("Asset text value:", value)
        """
        return storage.get_text(name)

    @keyword("Set JSON Asset")
    def set_json_asset(self, name: str, value: Dict, wait: bool = True):
        """Creates or updates an asset named `name` with the provided dictionary
        `value`.

        :param name: Name of the existing or new asset to create (if missing)
        :param value: The new dictionary value to set within the asset
        :param wait: Wait for the value to be set successfully

        **Example: Robot Framework**

        .. code-block:: robotframework

            *** Tasks ***
            Set An Asset
                &{entries} =    Create Dictionary   dogs    ${10}
                Set JSON Asset    my-json-asset    ${entries}

        **Example: Python**

        .. code-block:: python

            def set_an_asset():
                entries = {"dogs": 10}
                storage.set_json_asset("my-json-asset", entries)
        """
        storage.set_json(name, value=value, wait=wait)

    @keyword("Get JSON Asset")
    def get_json_asset(self, name: str) -> Dict:
        """Get the asset's dictionary value by providing its `name`.

        :param name: Name of the asset
        :raises AssetNotFound: Asset with the given name does not exist
        :returns: The current value of this asset as a dictionary

        **Example: Robot Framework**

        .. code-block:: robotframework

            *** Tasks ***
            Retrieve An Asset
                &{value} =      Get JSON Asset       my-json-asset
                Log     Asset dictionary value: ${value}

        **Example: Python**

        .. code-block:: python

            def retrieve_an_asset():
                value = storage.get_json_asset("my-json-asset")
                print("Asset dictionary value:", value)
        """
        return storage.get_json(name)

    @keyword
    def set_file_asset(self, name: str, path: str, wait: bool = True):
        """Creates or updates an asset named `name` with the content of the given
        `path` file.

        :param name: Name of the existing or new asset to create (if missing)
        :param path: The file path whose content to be set within the asset
        :param wait: Wait for the value to be set successfully

        **Example: Robot Framework**

        .. code-block:: robotframework

            *** Tasks ***
            Set An Asset
                Set File Asset    my-file-asset      report.pdf

        **Example: Python**

        .. code-block:: python

            def set_an_asset():
                storage.set_file_asset("my-file-asset", "report.pdf")
        """
        storage.set_file(name, path=path, wait=wait)

    @keyword
    def get_file_asset(self, name: str, path: str, overwrite: bool = False) -> str:
        """Get the asset's content saved to disk by providing its `name`.

        :param name: Name of the asset
        :param path: Destination path to the downloaded file
        :param overwrite: Replace destination file if it already exists (default False)
        :raises AssetNotFound: Asset with the given name does not exist
        :returns: A local path pointing to the retrieved file

        **Example: Robot Framework**

        .. code-block:: robotframework

            *** Tasks ***
            Retrieve An Asset
                ${path} =      Get File Asset       my-file-asset    report.pdf
                Log     Asset file path: ${path}

        **Example: Python**

        .. code-block:: python

            def retrieve_an_asset():
                path = storage.get_file_asset("my-file-asset", "report.pdf")
                print("Asset file path:", path)
        """
        return str(storage.get_file(name, path=path, exist_ok=overwrite))

    @keyword
    def delete_asset(self, name: str):
        """Delete an asset by providing its `name`.

        This operation cannot be undone.

        :param name: Name of the asset to delete
        :raises AssetNotFound: Asset with the given name does not exist

        **Example: Robot Framework**

        .. code-block:: robotframework

            *** Tasks ***
            Remove An Asset
                Delete Asset    my-asset

        **Example: Python**

        .. code-block:: python

            def remove_an_asset():
                storage.delete_asset("my-asset")
        """
        storage.delete_asset(name)
