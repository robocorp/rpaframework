# pylint: disable=missing-class-docstring
import logging
import platform


if platform.system() == "Windows":
    from SapGuiLibrary import SapGuiLibrary
else:

    class SapGuiLibrary:
        """Keywords are only available in Windows."""

        def __init__(self, *args, **kwargs):
            del args, kwargs


class SAP(SapGuiLibrary):
    __doc__ = (
        "This library wraps the upstream "
        "[https://frankvanderkuur.github.io/SapGuiLibrary.html|SapGuiLibrary]."
        "\n\n" + SapGuiLibrary.__doc__
    )

    ROBOT_LIBRARY_SCOPE = "GLOBAL"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = logging.getLogger(__name__)

        if platform.system() != "Windows":
            self.logger.warning("SAP requires Windows dependencies to work.")
