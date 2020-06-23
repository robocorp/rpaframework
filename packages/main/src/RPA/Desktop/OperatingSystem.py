from collections import OrderedDict
import datetime
import getpass
import logging
import os
import platform
import socket

from RPA.core.decorators import operating_system_required

if platform.system() == "Windows":
    import psutil
    from psutil._common import bytes2human
else:
    psutil = object
    bytes2human = object


class OperatingSystem:
    """RPA Framework library containing cross platform keywords for managing
    computer properties and actions.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    @operating_system_required("Windows")
    def get_boot_time(self, as_datetime=False, datetime_format="%Y-%m-%d %H:%M:%S"):
        """Get computer boot time in seconds from Epoch or in datetime string.

        :param as_datetime: if True returns datetime string, otherwise seconds,
            defaults to False
        :param datetime_format: datetime string format, defaults to "%Y-%m-%d %H:%M:%S"
        :return: seconds from Epoch or datetime string
        """
        btime = self.boot_time_in_seconds_from_epoch()
        if as_datetime:
            return datetime.datetime.fromtimestamp(btime).strftime(datetime_format)
        return btime

    @operating_system_required("Windows")
    def boot_time_in_seconds_from_epoch(self):
        """Get machine boot time

        :return: boot time in seconds from Epoch
        """
        return psutil.boot_time()

    def get_machine_name(self):
        """Get machine name

        :return: machine name as string
        """
        return socket.gethostname()

    def get_username(self):
        """Get username of logged in user

        :return: username as string
        """
        return getpass.getuser()

    @operating_system_required("Darwin", "Linux")
    def put_system_to_sleep(self):
        if platform.system() == "Darwin":
            os.system("pmset sleepnow")
        if platform.system() == "Linux":
            os.system("systemctl suspend")

    @operating_system_required("Windows")
    def process_exists(self, process_name):
        """Check if process exists by its name

        :param process_name: search for this process
        :return: process instance or False
        """
        for p in psutil.process_iter():
            p_name = p.name()
            if p_name.lower() == process_name.lower():
                return p
        return False

    @operating_system_required("Windows")
    def kill_process(self, process_name):
        """Kill process by name

        :param process_name:
        :return: True if succeeds False if not
        """
        p = self.process_exists(process_name)
        if p:
            p.terminate()
            return True
        return False

    @operating_system_required("Windows")
    def get_memory_stats(self, humanized=True):
        """Get computer memory stats and return those in bytes
        or in humanized memory format.

        :param humanized: if False returns memory information in bytes, defaults to True
        :return: memory information in dictionary format
        """
        meminfo = psutil.virtual_memory()
        memdict = meminfo._asdict()
        if humanized:
            humandict = {}
            for key, val in memdict.items():
                if key == "percent":
                    humandict[key] = val
                else:
                    humandict[key] = bytes2human(val)
            return OrderedDict(humandict)
        return memdict
