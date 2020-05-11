from io import StringIO
import logging
import mimetypes
import os
import time
from email import encoders, message_from_bytes
from email.charset import add_charset, QP
from email.generator import Generator
from email.header import Header
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from pathlib import Path
from imaplib import IMAP4_SSL
from smtplib import SMTP, SMTP_SSL, ssl
from smtplib import SMTPConnectError, SMTPNotSupportedError, SMTPServerDisconnected

from typing import Any

from robot.libraries.BuiltIn import BuiltIn, RobotNotRunningError
from RPA.RobotLogListener import RobotLogListener


IMAGE_FORMATS = ["jpg", "jpeg", "bmp", "png", "gif"]

try:
    BuiltIn().import_library("RPA.RobotLogListener")
except RobotNotRunningError:
    pass


class ImapSmtp:
    """RPA Framework library providing SMTP and IMAP operations for
    specified mail server.

    Proper initialization needs `smtp_server` and `imap_server` defined.
    """

    def __init__(
        self,
        smtp_server: str = None,
        port: int = 587,
        imap_server: str = None,
        account: str = None,
        password: str = None,
    ) -> None:
        listener = RobotLogListener()
        listener.register_protected_keywords(
            ["RPA.Email.ImapSmtp.authorize", "RPA.Email.ImapSmtp.set_credentials"]
        )

        self.logger = logging.getLogger(__name__)
        self.smtp_server = smtp_server
        self.imap_server = imap_server
        self.port = int(port)
        self.set_credentials(account, password)
        self.smtp_conn = None
        self.imap_conn = None

    def __del__(self) -> None:
        if self.smtp_conn:
            try:
                self.smtp_conn.quit()
            except SMTPServerDisconnected:
                self.logger.debug("Was already disconnected")
            finally:
                self.smtp_conn = None

        if self.imap_conn:
            self.imap_conn.close()
            self.imap_conn.logout()
            self.imap_conn = None

    def set_credentials(self, account: str = None, password: str = None) -> None:
        """Set credentials

        :param account: user account as string, defaults to None
        :param password: user password as string, defaults to None
        """
        if account:
            self.account = account
        if password:
            self.password = password

    def authorize_smtp(
        self,
        account: str = None,
        password: str = None,
        smtp_server: str = None,
        smtp_port: int = None,
    ) -> None:
        """Authorize to SMTP server.

        Can be called without giving any parameters if library
        has been initialized with necessary information and/or
        keyword ``set_credentials`` has been used.

        :param account: SMTP account name, defaults to None
        :param password: SMTP account password, defaults to None
        :param smtp_server: SMTP server address, defaults to None
        :param smtp_port: SMTP server port, defaults to None (587 for SMTP)
        """
        if account is None and password is None:
            account = self.account
            password = self.password
        if smtp_server is None:
            smtp_server = self.smtp_server
        if smtp_port is None:
            smtp_port = self.port
        else:
            smtp_port = int(smtp_port)
        if smtp_server and account and password:
            try:
                self.smtp_conn = SMTP(smtp_server, smtp_port)
                self.send_smtp_hello()
                try:
                    self.smtp_conn.starttls()
                except SMTPNotSupportedError:
                    self.logger.warning("SMTP not supported by the server")
            except SMTPConnectError:
                context = ssl.create_default_context()
                self.smtp_conn = SMTP_SSL(smtp_server, smtp_port, context=context)
            self.smtp_conn.login(account, password)
        else:
            self.logger.warning(
                "Server address, account and password are needed for "
                "authentication with SMTP"
            )
        if self.smtp_conn is None:
            self.logger.warning("Not able to establish SMTP connection")

    def authorize_imap(
        self, account: str = None, password: str = None, imap_server: str = None
    ) -> None:
        """Authorize to IMAP server.

        Can be called without giving any parameters if library
        has been initialized with necessary information and/or
        keyword ``set_credentials`` has been used.

        :param account: IMAP account name, defaults to None
        :param password: IMAP account password, defaults to None
        :param smtp_server: IMAP server address, defaults to None
        """
        if account is None and password is None:
            account = self.account
            password = self.password
        if imap_server is None:
            imap_server = self.imap_server
        if imap_server and account and password:
            self.imap_conn = IMAP4_SSL(imap_server)
            self.imap_conn.login(account, password)
            self.imap_conn.select("inbox")
        else:
            self.logger.warning(
                "Server address, account and password are needed for "
                "authentication with IMAP"
            )
        if self.imap_conn is None:
            self.logger.warning("Not able to establish IMAP connection")

    def authorize(
        self,
        account: str = None,
        password: str = None,
        smtp_server: str = None,
        imap_server: str = None,
    ) -> None:
        """Authorize user to SMTP and IMAP servers.

        Will use separately set credentials or those given in keyword call.

        :param account: user account as string, defaults to None
        :param password: user password as string, defaults to None
        """
        self.authorize_smtp(account, password, smtp_server)
        self.authorize_imap(account, password, imap_server)

    def send_smtp_hello(self) -> None:
        """Send hello message to SMTP server.

        Required step when creating SMTP connection.
        """
        if self.smtp_conn:
            self.smtp_conn.ehlo()

    def send_message(
        self,
        sender: str,
        recipients: str,
        subject: str,
        body: str,
        attachments: str = None,
        html: bool = False,
    ) -> None:
        """Send SMTP email

        Valid sender values:
            - First Lastname <address@domain>
            - address@domain

        :param sender: who is sending, ie. 'from'
        :param recipients: who is receiving, ie. 'to'
        :param subject: mail subject field
        :param body: mail body content
        :param attachments: list of filepaths to attach, defaults to []
        :param html: if message content is in HTML, default `False`
        """
        if self.smtp_conn is None:
            raise ValueError("Requires authorized SMTP connection")
        add_charset("utf-8", QP, QP, "utf-8")
        attachments = attachments or []
        if not isinstance(attachments, list):
            attachments = attachments.split(",")

        msg = MIMEMultipart()

        if len(attachments) > 0:
            for filename in attachments:
                self.logger.debug("Adding attachment: %s", filename)
                with open(filename, "rb") as attachment:
                    _, ext = filename.lower().rsplit(".", 1)
                    ctype, _ = mimetypes.guess_type(filename)
                    _, subtype = ctype.split("/", 1)
                    if ext in IMAGE_FORMATS:
                        # image attachment
                        part = MIMEImage(
                            attachment.read(),
                            name=os.path.basename(filename),
                            _subtype=subtype,
                        )
                    else:
                        # attach other filetypes
                        part = MIMEBase("application", "octet-stream")
                        part.set_payload(attachment.read())
                        encoders.encode_base64(part)
                    part.add_header(
                        "Content-Disposition",
                        f"attachment; filename= {Path(filename).name}",
                    )
                    msg.attach(part)

        msg["From"] = sender
        msg["Subject"] = Header(subject, "utf-8")

        if html:
            htmlpart = MIMEText(body, "html", "UTF-8")
            msg.attach(htmlpart)
        else:
            textpart = MIMEText(body, "plain", "UTF-8")
            msg.attach(textpart)

        # Create a generator and flatten message object to 'file’
        str_io = StringIO()
        g = Generator(str_io, False)
        g.flatten(msg)

        if not isinstance(recipients, list):
            recipients = recipients.split(",")
        try:
            self.smtp_conn.sendmail(sender, recipients, str_io.getvalue())
        except Exception as err:
            raise ValueError(f"Send Message failed: {err}")

    def _fetch_messages(self, mail_ids: list) -> list:
        messages = []
        for mail_id in mail_ids:
            _, data = self.imap_conn.fetch(mail_id, "(RFC822)")
            message = message_from_bytes(data[0][1])
            messages.append(message)
        return messages

    def _search_message(self, criterion: str) -> list:
        return self.imap_conn.search(None, "(" + criterion + ")")

    def _delete_message(self, mail_ids: list) -> None:
        for mail_id in mail_ids:
            self.imap_conn.store(mail_id, "+FLAGS", "\\Deleted")
        self.imap_conn.expunge()

    def delete_message(self, criterion: str = "") -> bool:
        """Delete single message from server based on criterion.

        If criterion does not return exactly 1 message then delete is not done.

        :param criterion: filter messages based on this, defaults to ""
        :return: True if success, False if not
        """
        if self.imap_conn is None:
            raise ValueError("Requires authorized IMAP connection")
        if len(criterion) < 1:
            self.logger.warning(
                "Delete message requires criteria which message is affected."
            )
            return False
        _, data = self._search_message(criterion)
        mail_ids = data[0].split()
        if len(mail_ids) != 1:
            self.logger.warning(
                "Delete message criteria matched %d messages. Not deleting.",
                len(mail_ids),
            )
            return False
        else:
            self._delete_message(mail_ids)
            return True

    def delete_messages(self, criterion: str = "") -> bool:
        """Delete messages from server based on criterion.

        :param criterion: filter messages based on this, defaults to ""
        :return: True if success, False if not
        """
        if self.imap_conn is None:
            raise ValueError("Requires authorized IMAP connection")
        if len(criterion) < 1:
            self.logger.warning(
                "Delete messages requires criteria which messages are affected."
            )
            return False
        _, data = self._search_message(criterion)
        mail_ids = data[0].split()
        self._delete_message(mail_ids)
        return True

    def save_messages(self, criterion: str = "", target_folder: str = None) -> bool:
        """Save messages based on criteria and store them to target folder
        with attachment files.

        Does not save message if `target_folder` is not given.

        :param criterion: filter messages based on this, defaults to ""
        :param target_folder: path to folder where message are saved, defaults to None
        :return: True if success, False if not
        """
        if self.imap_conn is None:
            raise ValueError("Requires authorized IMAP connection")
        if len(criterion) < 1:
            self.logger.warning(
                "Save messages requires criteria for which messages to store locally."
            )
            return False
        if target_folder is None:
            target_folder = os.path.expanduser("~")
        _, data = self._search_message(criterion)
        mail_ids = data[0].split()
        for mail_id in mail_ids:
            _, data = self.imap_conn.fetch(mail_id, "(RFC822)")
            emlfile = Path(target_folder) / f"{str(int(mail_id))}.eml"
            with open(emlfile, "wb") as f:
                f.write(data[0][1])
        return True

    def list_messages(self, criterion: str = "") -> Any:
        """Return list of messages matching criterion.

        :param criterion: list emails matching this, defaults to ""
        :return: list of messages or False
        """
        if self.imap_conn is None:
            raise ValueError("Requires authorized IMAP connection")
        self.logger.info("List messages: %s", criterion)
        _, data = self._search_message(criterion)
        mail_ids = data[0].split()
        return self._fetch_messages(mail_ids)

    def save_attachments(
        self, criterion: str = "", target_folder: str = None, overwrite: bool = False
    ) -> Any:
        """Save mail attachments into local folder.

        :param criterion: attachments are saved for mails matching this, defaults to ""
        :param target_folder: local folder for saving attachments to (needs to exist),
            defaults to user's home directory if None
        :param overwrite: overwrite existing file is True, defaults to False
        :return: list of saved attachments or False
        """
        if self.imap_conn is None:
            raise ValueError("Requires authorized IMAP connection")
        attachments_saved = []
        if target_folder is None:
            target_folder = os.path.expanduser("~")
        messages = self.list_messages(criterion)
        for msg in messages:
            for part in msg.walk():
                content_maintype = part.get_content_maintype()
                content_disposition = part.get("Content-Disposition")
                if content_maintype != "multipart" and content_disposition is not None:
                    filename = part.get_filename()
                    self.logger.info("%s %s", filename, content_maintype)
                    if bool(filename):
                        filepath = Path(target_folder) / filename
                        if not filepath.exists() or overwrite:
                            with open(filepath, "wb") as f:
                                f.write(part.get_payload(decode=True))
                                attachments_saved.append(filepath)
        return attachments_saved if len(attachments_saved) > 0 else False

    def wait_for_message(
        self, criterion: str = "", timeout: float = 5.0, interval: float = 1.0
    ) -> Any:
        """Wait for email matching `criterion` to arrive into mailbox.

        Examples:
            - wait_for_message('SUBJECT "rpa task calling"', timeout=300, interval=10)

        :param criterion: message filter to wait for, defaults to ""
        :param timeout: total time in seconds to wait for email, defaults to 5.0
        :param interval: time in seconds for new check, defaults to 1.0
        :return: list of messages or False
        """
        if self.imap_conn is None:
            raise ValueError("Requires authorized IMAP connection")
        if len(criterion) < 1:
            self.logger.warning(
                "Wait for message requires criteria for which message to wait for."
            )
            return False
        end_time = time.time() + float(timeout)
        while time.time() < end_time:
            self.imap_conn.select("inbox")
            _, data = self._search_message(criterion)
            mail_ids = data[0].split()
            self.logger.warning(
                "Wait for message found matching message %d time(s).", len(mail_ids)
            )
            if len(mail_ids) > 0:
                return self._fetch_messages(mail_ids)
            time.sleep(interval)
        return False
