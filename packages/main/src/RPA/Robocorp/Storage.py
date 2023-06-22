from typing import List

from robocorp import storage
from robot.api.deco import keyword, library


@library
class Storage:
    """Control Room `Storage Asset` library operating with the cloud built-in key-value
    store.

    **Usage**

    .. code-block:: robotframework

        *** Tasks ***
        Manage Assets
            @{assets} =    List Assets
            Log List    ${assets}

            Set Asset    my-asset    My string asset value
            ${value} =      Get Asset       my-asset
            Log     Asset value: ${value}

            Delete Asset    my-asset

    .. code-block:: python

        import logging
        from RPA.Robocorp.Storage import Storage

        storage = Storage()

        def manage_assets():
            assets = storage.list_assets()
            logging.info(assets)

            storage.set_asset("my-asset", "My string asset value")
            value = storage.get_asset("my-asset")
            logging.info("Asset value: %s", value)

            storage.delete_asset("my-asset")

    **Caveats**

    We currently support text values only, therefore you need to serialize other types
    of values first. (e.g.: dumping a dictionary into a JSON string before setting it)
    """

    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    ROBOT_LIBRARY_DOC_FORMAT = "REST"

    @keyword
    def list_assets(self) -> List[storage.AssetMeta]:
        """List all the existing assets.

        :returns: A list of assets where each asset is a dictionary with fields like
            'id' and 'name'

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
    def get_asset(self, name: str) -> str:
        """Get an asset's value by providing its `name`.

        :param name: Name of the asset
        :raises AssetNotFound: Asset with the given name does not exist
        :returns: The previously set value of this asset, or empty string if not set

        **Example: Robot Framework**

        .. code-block:: robotframework

            *** Tasks ***
            Retrieve An Asset
                ${value} =      Get Asset       my-asset
                Log     Asset value: ${value}

        **Example: Python**

        .. code-block:: python

            def retrieve_an_asset():
                value = storage.get_asset("my-asset")
                print("Asset value:", value)
        """
        return storage.get_asset(name)

    @keyword
    def set_asset(self, name: str, value: str, wait: bool = True):
        """Creates or updates an asset named `name` with the provided `value`.

        :param name: Name of the existing or new asset to create (if missing)
        :param value: The new value to set within the asset
        :param wait: Wait for value to be set successfully

        **Example: Robot Framework**

        .. code-block:: robotframework

            *** Tasks ***
            Set An Asset
                Set Asset    my-asset    My string asset value

        **Example: Python**

        .. code-block:: python

            def set_an_asset():
                storage.set_asset("my-asset", "My string asset value")
        """
        storage.set_asset(name, value, wait=wait)

    @keyword
    def delete_asset(self, name: str):
        """Delete an asset by providing its `name`.

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
