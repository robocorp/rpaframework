from ftplib import FTP as FTPconn
from ftplib import FTP_TLS as TLSconn
from ftplib import all_errors, error_perm
from functools import wraps
import logging
import os
from typing import Tuple
from RPA.core.notebook import notebook_file


class AuthenticationException(Exception):
    """Raised when server authentication fails"""


class FTPException(Exception):
    """Raised on general FTP error"""


def ftpcommand(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if args[0].instance is None:
            raise FTPException("No FTP connection")
        try:
            ret = f(*args, **kwargs)
            return ret
        except FileNotFoundError as e:
            args[0].logger.warning(str(e))
            return False
        except error_perm as e:
            args[0].logger.warning(str(e))
            return False
        except all_errors as e:
            raise FTPException from e

    return wrapper


class FTP:
    """`FTP` library can be used to access an FTP server,
    and interact with files.

    The library is based on Python's built-in `ftplib`_.

    .. _ftplib: https://docs.python.org/3/library/ftplib.html

    **Examples**

    **Robot Framework**

    .. code-block:: robotframework

        *** Settings ***
        Library    RPA.FTP

        *** Variables ***
        ${HOST}       127.0.0.1
        ${PORT}       27345
        ${USER}       user
        ${PASS}       12345

        *** Tasks ***
        List files on the server directory
            Connect   ${HOST}  ${PORT}  ${USER}  ${PASS}
            @{files}  List Files
            FOR  ${file}  IN  @{files}
                Log  ${file}
            END

    **Python**

    .. code-block:: python

        from RPA.FTP import FTP

        library = FTP()
        library.connect('127.0.0.1', 27345, 'user', '12345')
        files = library.list_files()
        for f in files:
            print(f)
    """

    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    ROBOT_LIBRARY_DOC_FORMAT = "REST"

    def __init__(self):
        self.instance = None
        self.logger = logging.getLogger(__name__)

    def connect(
        self,
        host: str,
        port: int = 21,
        user: str = None,
        password: str = None,
        tls: bool = False,
        transfer: str = "passive",
        keyfile: str = None,
        certfile: str = None,
        timeout: int = None,
        source_address: Tuple[str, int] = None,
    ):
        """Connect to FTP server

        :param host: address of the server
        :param port: port of the server, defaults to 21
        :param user: login name, defaults to None
        :param password: login password, defaults to None
        :param tls: connect using TLS support, defaults to False
        :param transfer: mode of the transfer, defaults to "passive"
        :param keyfile: path to private key file
        :param certfile: path to certificate file
        :param timeout: a timeout in seconds for the connection attempt
        :param source_address: socket to bind to as its source address before connecting
        :raises AuthenticationException: on authentication error with the server
        """
        try:
            if tls:
                self.instance = TLSconn(
                    keyfile=keyfile,
                    certfile=certfile,
                    timeout=timeout,
                    source_address=source_address,
                )
            else:
                self.instance = FTPconn(timeout=timeout, source_address=source_address)
            self.instance.connect(host, port)
            if user and password:
                self.instance.login(user=user, passwd=password)
            else:
                self.instance.login()
            if tls:
                self.instance.prot_p()
            if transfer != "passive":
                self.instance.set_pasv(False)
        except error_perm as e:
            raise AuthenticationException from e
        except all_errors as e:
            raise FTPException from e

        self.logger.info("FTP connection successful")
        return True

    def quit(self):
        """Send QUIT command to the server and close connection"""
        try:
            self.instance.quit()
        except all_errors as e:
            self.logger.debug(str(e))
            self.close()
        finally:
            self.instance = None

    def close(self):
        """Close connection to the server unilaterally"""
        if self.instance:
            self.instance.close()
            self.instance = None

    @ftpcommand
    def upload(self, localfile: str, remotefile: str) -> bool:
        """Upload file to FTP server

        :param localfile: path to file to upload
        :param remotefile: name of uploaded file in the server
        """
        cmd = f"STOR {remotefile}"
        self.instance.storbinary(cmd, open(localfile, "rb"))

    def download(self, remotefile: str, localfile: str = None) -> bool:
        """Download file from FTP server

        :param remotefile: path to remote file on the server
        :param localfile: name of the downloaded file on the local filesystem,
            if `None` will have same name as remote file
        """
        if self.instance is None:
            raise FTPException("No FTP connection")
        try:
            cmd = f"RETR {remotefile}"
            if localfile is None:
                localfile = remotefile
            with open(localfile, "wb") as filepath:
                self.instance.retrbinary(cmd, filepath.write, 1024)
            notebook_file(localfile)
            return True
        except FileNotFoundError as e:
            self.logger.warning(str(e))
            return False
        except error_perm as e:
            self.logger.warning(str(e))
            os.unlink(localfile)
            return False
        except all_errors as e:
            raise FTPException from e

    @ftpcommand
    def cwd(self, dirname: str) -> bool:
        """Change working directory on the server

        :param dirname: name of the directory
        """
        self.instance.cwd(dirname)

    @ftpcommand
    def pwd(self) -> str:
        """Get current working directory on the server"""
        return self.instance.pwd()

    @ftpcommand
    def mkd(self, dirname: str) -> bool:
        """Create a new directory on the server

        :param dirname: name of the directory
        """
        self.instance.mkd(dirname)

    @ftpcommand
    def rmd(self, dirname: str) -> bool:
        """Remove directory on the server

        :param dirname: name of the directory
        """
        self.instance.rmd(dirname)

    @ftpcommand
    def list_files(self, dirname: str = "") -> list:
        """List files on the server directory

        :param dirname: name of the directory
        """
        try:
            return list(self.instance.mlsd(path=dirname))
        except all_errors:
            return list(self.instance.nlst())

    @ftpcommand
    def delete(self, filepath: str) -> bool:
        """Delete file on the server

        :param filepath: path to server file
        """
        self.instance.delete(filepath)

    @ftpcommand
    def rename(self, fromname: str, toname: str) -> bool:
        """Rename file on the server

        :param fromname: current name of the file
        :param toname: new name for the file
        """
        self.instance.rename(fromname, toname)

    @ftpcommand
    def send_command(self, command: str) -> bool:
        """Execute command on the server

        List of FTP commands:
        https://en.wikipedia.org/wiki/List_of_FTP_commands

        :param command: name of the command to send
        """
        return self.instance.sendcmd(command)

    @ftpcommand
    def file_size(self, filepath: str) -> int:
        """Return byte size of the file on the server

        :param filepath: path to server file
        """
        self.set_binary_mode()
        return self.instance.size(filepath)

    @ftpcommand
    def abort(self) -> bool:
        """Abort a file transfer in progress"""
        self.instance.abort()

    @ftpcommand
    def get_welcome_message(self) -> str:
        """Get server welcome message

        :return: welcome message
        """
        return self.instance.getwelcome()

    @ftpcommand
    def set_debug_level(self, level: int = 0) -> bool:
        """Set debug level for the library

        :param level: integer value of debug level, defaults to 0

        0 - no debugging output
        1 - moderate amount of debugging
        2+ - higher amount of debugging
        """
        if level >= 0:
            self.instance.set_debuglevel(level)
        else:
            self.logger.warning("Valid debug levels are 0, 1 or 2+")

    def set_ascii_mode(self):
        """Set transfer mode to ASCII"""
        self.send_command("TYPE a")

    def set_binary_mode(self):
        """Set transfer mode to BINARY"""
        self.send_command("TYPE i")
