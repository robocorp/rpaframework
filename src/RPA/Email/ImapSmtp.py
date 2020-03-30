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
from smtplib import SMTP, SMTP_SSL, ssl, SMTPConnectError, SMTPNotSupportedError

from robot.libraries.BuiltIn import BuiltIn, RobotNotRunningError
from RPA.RobotLogListener import RobotLogListener

IMAGE_FORMATS = ["jpg", "jpeg", "bmp", "png", "gif"]

try:
    BuiltIn().import_library("RPA.RobotLogListener")
except RobotNotRunningError:
    pass


class ImapSmtp:
    """RPA Framework library providing SMTP and IMAP operations for specified mail server.

    Proper initialization needs `smtp_server` and `imap_server` defined.
    """

    def __init__(
        self, smtp_server=None, port=587, imap_server=None, account=None, password=None
    ):
        listener = RobotLogListener()
        listener.register_protected_keywords(
            ["RPA.Email.ImapSmtp.Authorize", "RPA.Email.ImapSmtp.set_credentials"]
        )

        self.logger = logging.getLogger(__name__)
        self.smtp_server = smtp_server
        self.imap_server = smtp_server if imap_server is None else imap_server
        self.port = int(port)
        self.set_credentials(account, password)
        self.smtp_conn = None
        self.imap_conn = None

    def __del__(self):
        if self.smtp_conn:
            self.smtp_conn.quit()
        if self.imap_conn:
            self.imap_conn.close()
            self.imap_conn.logout()

    def set_credentials(self, account=None, password=None):
        """Set credentials for library

        :param account: user account as string, defaults to None
        :param password: user password as string, defaults to None
        """
        self.account = account
        self.password = password

    def authorize(self, account=None, password=None):
        """Authorize user into SMPT and IMAP servers.

        Will use separately set credentials or those given in keyword call.

        :param account: user account as string, defaults to None
        :param password: user password as string, defaults to None
        """
        if account and password:
            self.set_credentials(account, password)
        self.logger.debug(f"connect (SMTP): {self.smtp_server}:{self.port}")
        try:
            self.smtp_conn = SMTP(self.smtp_server, self.port)
            self.send_smtp_hello()
            try:
                self.smtp_conn.starttls()
            except SMTPNotSupportedError:
                self.logger.warning("SMTP not supported by the server")
        except SMTPConnectError:
            context = ssl.create_default_context()
            self.smtp_conn = SMTP_SSL(self.smtp_server, self.port, context=context)
        self.imap_conn = IMAP4_SSL(self.imap_server)
        if self.account and self.password:
            self.smtp_conn.login(self.account, self.password)
            self.imap_conn.login(self.account, self.password)
        self.imap_conn.select("inbox")

    def send_smtp_hello(self):
        """Send hello message to SMTP server.

        Required step when creating SMTP connection.
        """
        if self.smtp_conn:
            self.smtp_conn.ehlo()

    def send_message(self, sender, recipients, subject, body, attachments=None):
        """Send SMTP email

        Valid sender values:
            - First Lastname <address@domain>
            - address@domain

        :param sender: who is sending, ie. 'from'
        :param recipients: who is receiving, ie. 'to'
        :param subject: mail subject field
        :param body: mail body content
        :param attachments: list of filepaths to attach, defaults to []
        """
        add_charset("utf-8", QP, QP, "utf-8")
        attachments = attachments or []
        if not isinstance(attachments, list):
            attachments = [attachments]

        msg = MIMEMultipart("alternative")
        if len(attachments) > 0:
            for filename in attachments:
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
                        "Content-Disposition", f"attachment; filename= {filename}"
                    )
                    msg.attach(part)

        msg["From"] = sender
        msg["Subject"] = Header(subject, "utf-8")
        htmlpart = MIMEText(body, "html", "UTF-8")
        textpart = MIMEText(body, "plain", "UTF-8")
        msg.attach(htmlpart)
        msg.attach(textpart)

        # Create a generator and flatten message object to 'file’
        str_io = StringIO()
        g = Generator(str_io, False)
        g.flatten(msg)

        self.smtp_conn.sendmail("", recipients, str_io.getvalue())

    def _fetch_messages(self, mail_ids):
        messages = []
        for mail_id in mail_ids:
            _, data = self.imap_conn.fetch(mail_id, "(RFC822)")
            message = message_from_bytes(data[0][1])
            messages.append(message)
        return messages

    def _search_message(self, criterion):
        return self.imap_conn.search(None, "(" + criterion + ")")

    def _delete_message(self, mail_ids):
        for mail_id in mail_ids:
            self.imap_conn.store(mail_id, "+FLAGS", "\\Deleted")
        self.imap_conn.expunge()

    def delete_message(self, criterion=""):
        """Delete single message from server based on criterion.

        If criterion does not return exactly 1 message then delete is not done.

        :param criterion: filter messages based on this, defaults to ""
        :return: True if success, False if not
        """
        if len(criterion) < 1:
            self.logger.warning(
                "Delete message requires criteria which message is affected."
            )
            return False
        _, data = self._search_message(criterion)
        mail_ids = data[0].split()
        if len(mail_ids) != 1:
            self.logger.warning(
                f"Delete message criteria matched {len(mail_ids)} messages. "
                "Not deleting."
            )
            return False
        else:
            self._delete_message(mail_ids)
            return True

    def delete_messages(self, criterion=""):
        """Delete messages from server based on criterion.

        :param criterion: filter messages based on this, defaults to ""
        :return: True if success, False if not
        """
        if len(criterion) < 1:
            self.logger.warning(
                "Delete messages requires criteria which messages are affected."
            )
            return False
        _, data = self._search_message(criterion)
        mail_ids = data[0].split()
        self._delete_message(mail_ids)
        return True

    def save_messages(self, criterion="", target_folder=None):
        """Save messages based on criteria and store them to target folder
        with attachment files.

        Does not save message if `target_folder` is not given.

        :param criterion: filter messages based on this, defaults to ""
        :param target_folder: path to folder where message are saved, defaults to None
        :return: True if success, False if not
        """
        if len(criterion) < 1:
            self.logger.warning(
                "Get messages requires criteria for which messages to store locally."
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

    def list_messages(self, criterion=""):
        """Return list of messages matching criterion.

        :param criterion: list emails matching this, defaults to ""
        :return: list of messages or False
        """
        self.logger.info(f"List messages: {criterion}")
        _, data = self._search_message(criterion)
        mail_ids = data[0].split()
        return self._fetch_messages(mail_ids)

    def save_attachments(self, criterion="", target_folder=None, overwrite=False):
        """Save mail attachments into local folder.

        :param criterion: attachments are saved for mails matching this, defaults to ""
        :param target_folder: local folder for saving attachments to (needs to exist),
            defaults to user's home directory if None
        :param overwrite: overwrite existing file is True, defaults to False
        :return: list of saved attachments or False
        """
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
                    self.logger.info(f"{filename} {content_maintype}")
                    if bool(filename):
                        filepath = Path(target_folder) / filename
                        if not filepath.exists() or overwrite:
                            with open(filepath, "wb") as f:
                                f.write(part.get_payload(decode=True))
                                attachments_saved.append(filepath)
        return attachments_saved if len(attachments_saved) > 0 else False

    def wait_for_message(self, criterion="", timeout=5.0, interval=1.0):
        """Wait for email matching `criterion` to arrive into mailbox.

        Examples:
            - wait_for_message('SUBJECT "rpa task calling"', timeout=300, interval=10)

        :param criterion: message filter to wait for, defaults to ""
        :param timeout: total time in seconds to wait for email, defaults to 5.0
        :param interval: time in seconds for new check, defaults to 1.0
        :return: list of messages or False
        """
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
                f"Wait for message found matching message {len(mail_ids)} time(s)."
            )
            if len(mail_ids) > 0:
                return self._fetch_messages(mail_ids)
            time.sleep(interval)
        return False
