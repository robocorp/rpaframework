# pylint: disable=unused-import
# flake8: noqa
import logging
from RPA.Robocorp.WorkItems import (
    WorkItem,
    BaseAdapter,
    FileAdapter,
    RobocorpAdapter,
    WorkItems as _WorkItems,
)


class Items(_WorkItems):
    __doc__ = _WorkItems.__doc__

    def __init__(self, *args, **kwargs):
        logging.warning(
            "This is a deprecated import that will "
            "be removed in favor of RPA.Robocorp.WorkItems"
        )
        super().__init__(*args, **kwargs)
