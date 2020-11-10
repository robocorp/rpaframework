from functools import wraps

from io import StringIO
import logging
import os
import re
import time

# email package declares these properties in the __all__ definition but
# pylint ignores that
from email import encoders, message_from_bytes  # pylint: disable=E0611
from email.charset import add_charset, QP  # pylint: disable=E0611
from email.generator import Generator  # pylint: disable=E0611
from email.header import Header, decode_header, make_header  # pylint: disable=E0611
from email.mime.base import MIMEBase  # pylint: disable=E0611
from email.mime.image import MIMEImage  # pylint: disable=E0611
from email.mime.multipart import MIMEMultipart  # pylint: disable=E0611
from email.mime.text import MIMEText  # pylint: disable=E0611

from pathlib import Path
from imaplib import IMAP4_SSL
from smtplib import SMTP, SMTP_SSL, ssl
from smtplib import SMTPConnectError, SMTPNotSupportedError, SMTPServerDisconnected

from typing import Any

from robot.libraries.BuiltIn import BuiltIn, RobotNotRunningError
from RPA.RobotLogListener import RobotLogListener


IMAGE_FORMATS = ["jpg", "jpeg", "bmp", "png", "gif"]
FLAG_DELETED = "\\Deleted"
FLAG_SEEN = "\\Seen"
FLAG_FLAGGED = "\\Flagged"

try:
    BuiltIn().import_library("RPA.RobotLogListener")
except RobotNotRunningError:
    pass


def imap_connection(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if args[0].imap_conn is None:
            raise ValueError("Requires authorized IMAP connection")
        return f(*args, **kwargs)

    return wrapper


def smtp_connection(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if args[0].smtp_conn is None:
            raise ValueError("Requires authorized SMTP connection")
        return f(*args, **kwargs)

    return wrapper


class ImapSmtp:
    """`ImapSmtp` is a library for sending, reading, and deleting emails.
    `ImapSmtp` is interfacing with SMTP and IMAP protocols.

    **Troubleshooting**

    - Authentication error with Gmail - "Application-specific password required"
        see. https://support.google.com/mail/answer/185833?hl=en

    **Examples**

    **Robot Framework**

    It is highly recommended to secure your passwords and take care
    that they are not stored in the version control by mistake.
    See ``RPA.Robocloud.Secrets`` how to store RPA Secrets into Robocloud.

    When sending HTML content with IMG tags, the ``src`` filenames must match
    the base image name given with the ``images`` parameter.

    .. code-block:: robotframework

        *** Settings ***
        Library     RPA.Email.ImapSmtp   smtp_server=smtp.gmail.com  port=587
        Task Setup  Authorize  account=${GMAIL_ACCOUNT}  password=${GMAIL_PASSWORD}

        *** Variables ***
        ${GMAIL_ACCOUNT}        ACCOUNT_NAME
        ${GMAIL_PASSWORD}       ACCOUNT_PASSWORD
        ${RECIPIENT_ADDRESS}    RECIPIENT
        ${BODY_IMG1}            ${IMAGEDIR}${/}approved.png
        ${BODY_IMG2}            ${IMAGEDIR}${/}invoice.png
        ${EMAIL_BODY}     <h1>Heading</h1><p>Status: <img src='approved.png' alt='approved image'/></p>
        ...               <p>INVOICE: <img src='invoice.png' alt='invoice image'/></p>

        *** Tasks ***
        Sending email
            Send Message  sender=${GMAIL_ACCOUNT}
            ...           recipients=${RECIPIENT_ADDRESS}
            ...           subject=Message from RPA Robot
            ...           body=RPA Robot message body

        Sending HTML Email With Image
            [Documentation]     Sending email with HTML content and attachment
            Send Message
            ...                 sender=${GMAIL_ACCOUNT}
            ...                 recipients=${RECIPIENT_ADDRESS}
            ...                 subject=HTML email with body images (2) plus one attachment
            ...                 body=${EMAIL_BODY}
            ...                 html=${TRUE}
            ...                 images=${BODY_IMG1}, ${BODY_IMG2}
            ...                 attachments=example.png

    **Python**

    .. code-block:: python

        from RPA.Email.ImapSmtp import ImapSmtp

        gmail_account = "ACCOUNT_NAME"
        gmail_password = "ACCOUNT_PASSWORD"
        sender = gmail_account

        mail = ImapSmtp(smtp_server="smtp.gmail.com", port=587)
        mail.authorize(account=gmail_account, password=gmail_password)
        mail.send_message(
            sender=gmail_account,
            recipients="RECIPIENT",
            subject="Message from RPA Python",
            body="RPA Python message body",
        )
    """  # noqa: E501

    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    ROBOT_LIBRARY_DOC_FORMAT = "REST"

    def __init__(
        self,
        smtp_server: str = None,
        smtp_port: int = 587,
        imap_server: str = None,
        imap_port: int = 993,
        account: str = None,
        password: str = None,
    ) -> None:
        listener = RobotLogListener()
        listener.register_protected_keywords(
            ["RPA.Email.ImapSmtp.authorize", "RPA.Email.ImapSmtp.set_credentials"]
        )

        self.logger = logging.getLogger(__name__)
        self.smtp_server = smtp_server
        self.imap_server = imap_server if imap_server else smtp_server
        self.smtp_port = int(smtp_port)
        self.imap_port = int(imap_port)
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
            self.select_folder()
            self.imap_conn.close()
            self.imap_conn.logout()
            self.imap_conn = None

    def set_credentials(self, account: str = None, password: str = None) -> None:
        """Set credentials

        :param account: user account as string, defaults to None
        :param password: user password as string, defaults to None

        Example:

        .. code-block:: robotframework

            Set Credentials   ${username}   ${password}
            Authorize
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

        :param account: SMTP account name, defaults to None
        :param password: SMTP account password, defaults to None
        :param smtp_server: SMTP server address, defaults to None
        :param smtp_port: SMTP server port, defaults to None (587 for SMTP)

        Can be called without giving any parameters if library
        has been initialized with necessary information and/or
        keyword ``Set Credentials`` has been called.

        Example:

        .. code-block:: robotframework

            Authorize SMTP    ${username}   ${password}  smtp.gmail.com  587
        """
        if account is None and password is None:
            account = self.account
            password = self.password
        if smtp_server is None:
            smtp_server = self.smtp_server
        if smtp_port is None:
            smtp_port = self.smtp_port
        else:
            smtp_port = int(smtp_port)
        if smtp_server and account and password:
            try:
                self.smtp_conn = SMTP(smtp_server, smtp_port)
                self.send_smtp_hello()
                try:
                    self.smtp_conn.starttls()
                except SMTPNotSupportedError:
                    self.logger.warning("TLS not supported by the server")
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
        self,
        account: str = None,
        password: str = None,
        imap_server: str = None,
        imap_port: int = None,
    ) -> None:
        """Authorize to IMAP server.

        :param account: IMAP account name, defaults to None
        :param password: IMAP account password, defaults to None
        :param imap_server: IMAP server address, defaults to None
        :param imap_port: IMAP server port, defaults to None

        Can be called without giving any parameters if library
        has been initialized with necessary information and/or
        keyword ``Set Credentials`` has been called.

        Example:

        .. code-block:: robotframework

            Authorize IMAP    ${username}   ${password}  imap.gmail.com  993
        """
        if account is None and password is None:
            account = self.account
            password = self.password
        if imap_server is None:
            imap_server = self.imap_server
        if imap_port is None:
            imap_port = self.imap_port
        else:
            imap_port = int(imap_port)
        if imap_server and account and password:
            self.imap_conn = IMAP4_SSL(imap_server, imap_port)
            self.imap_conn.login(account, password)
            self.imap_conn.select("INBOX")
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
        smtp_port: int = None,
        imap_port: int = None,
    ) -> None:
        # pylint: disable=C0301
        """Authorize user to SMTP and IMAP servers.

        :param account: user account as string, defaults to None
        :param password: user password as string, defaults to None
        :param smtp_server: SMTP server address, defaults to None
        :param imap_server: IMAP server address, defaults to None
        :param smtp_port: SMTP server port, defaults to None (587 for SMTP)
        :param imap_port: IMAP server port, defaults to None

        Will use separately set credentials or those given in keyword call.

        Example:

        .. code-block:: robotframework

            Authorize    ${username}   ${password}  smtp_server=smtp.gmail.com  smtp_port=587
        """  # noqa: E501
        self.authorize_smtp(account, password, smtp_server, smtp_port)
        self.authorize_imap(account, password, imap_server, imap_port)

    @smtp_connection
    def send_smtp_hello(self) -> None:
        """Send hello message to SMTP server.

        Required step when creating SMTP connection.
        """
        if self.smtp_conn:
            self.smtp_conn.ehlo()

    @smtp_connection
    def send_message(
        self,
        sender: str,
        recipients: str,
        subject: str = "",
        body: str = "",
        attachments: str = None,
        html: bool = False,
        images: str = None,
    ) -> bool:
        """Send SMTP email

        :param sender: who is sending, ie. 'from'
        :param recipients: who is receiving, ie. 'to'
        :param subject: mail subject field
        :param body: mail body content
        :param attachments: list of filepaths to attach, defaults to []
        :param html: if message content is in HTML, default `False`
        :param images: list of filepaths for inline use, defaults to []

        Valid sender values:

        - First Lastname <address@domain>
        - address@domain

        Example:

        .. code-block:: robotframework

            Send Message  sender@domain.com  recipient@domain.com
            ...           subject=Greetings Software Robot Developer
            ...           body=${email_body}
            ...           attachments:${CURDIR}${/}report.pdf
        """
        add_charset("utf-8", QP, QP, "utf-8")
        recipients, attachments, images = self._handle_message_parameters(
            recipients, attachments, images
        )
        msg = MIMEMultipart()

        self._add_attachments_to_msg(attachments, msg)

        msg["From"] = sender
        msg["To"] = ",".join(recipients)
        msg["Subject"] = Header(subject, "utf-8")

        if html:
            for im in images:
                im = im.strip()
                imname = Path(im).name
                body = body.replace(str(imname), f"cid:{imname}")
                with open(im, "rb") as f:
                    img = MIMEImage(f.read())
                    img.add_header("Content-ID", f"<{imname}>")
                    msg.attach(img)
            htmlpart = MIMEText(body, "html", "UTF-8")
            msg.attach(htmlpart)
        else:
            textpart = MIMEText(body, "plain", "UTF-8")
            msg.attach(textpart)
            for im in images:
                im = im.strip()
                imname = Path(im).name
                with open(im, "rb") as f:
                    img = MIMEImage(f.read())
                    msg.add_header(
                        "Content-Disposition",
                        f"inline; filename= {imname}",
                    )
                    msg.attach(img)

        # Create a generator and flatten message object to 'file’
        str_io = StringIO()
        g = Generator(str_io, False)
        g.flatten(msg)

        try:
            self.smtp_conn.sendmail(sender, recipients, str_io.getvalue())
        except Exception as err:
            raise ValueError(f"Send Message failed: {err}") from err
        return True

    def _handle_message_parameters(self, recipients, attachments, images):
        if attachments is None:
            attachments = []
        if images is None:
            images = []
        if not isinstance(recipients, list):
            recipients = recipients.split(",")
        if not isinstance(attachments, list):
            attachments = str(attachments).split(",")
        if not isinstance(images, list):
            images = str(images).split(",")
        return recipients, attachments, images

    def _add_attachments_to_msg(self, attachments: list = None, msg=None):
        if len(attachments) > 0:
            for filename in attachments:
                if os.path.dirname(filename) == "":
                    filename = str(Path.cwd() / filename)
                self.logger.debug("Adding attachment: %s", filename)
                with open(filename, "rb") as attachment:
                    _, ext = filename.lower().rsplit(".", 1)
                    if ext in IMAGE_FORMATS:
                        # image attachment
                        part = MIMEImage(
                            attachment.read(),
                            name=Path(filename).name,
                            _subtype=ext,
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

    @imap_connection
    def _fetch_messages(self, mail_ids: list) -> list:
        messages = []
        for mail_id in mail_ids:
            _, data = self.imap_conn.fetch(mail_id, "(RFC822)")
            message = message_from_bytes(data[0][1])
            message_dict = {"Mail-Id": mail_id, "Message": message}
            for k, v in message.items():
                msg_item = decode_header(v)
                message_dict[k] = make_header(msg_item)
            message_dict["Body"], has_attachments = self._get_decoded_email_body(
                message
            )
            message_dict["Has-Attachments"] = has_attachments
            messages.append(message_dict)
        return messages

    def _get_decoded_email_body(self, message):
        """Decode email body.

        :param message_body: Raw 7-bit message body input e.g. from imaplib. Double
            encoded in quoted-printable and latin-1
        :return: Message body as unicode string and information if message has
            attachments

        Detect character set if the header is not set.
        We try to get text/plain, but if there is not one then fallback to text/html.
        """
        text = ""
        has_attachments = False
        if message.is_multipart():
            html = None

            for part in message.walk():
                # content_maintype = part.get_content_maintype()
                content_disposition = part.get("Content-Disposition")
                if content_disposition and "attachment" in content_disposition:
                    has_attachments = True
                    continue
                if part.get_content_charset() is None:
                    # We cannot know the character set, so return decoded "something"
                    text = part.get_payload(decode=True)
                    continue

                charset = part.get_content_charset()

                if part.get_content_type() == "text/plain":
                    text = str(
                        part.get_payload(decode=True), str(charset), "ignore"
                    ).encode("utf8", "replace")

                if part.get_content_type() == "text/html":
                    html = str(
                        part.get_payload(decode=True), str(charset), "ignore"
                    ).encode("utf8", "replace")

            if text:
                return (
                    (text.strip(), has_attachments) if text else ("", has_attachments)
                )
            else:
                return (
                    (html.strip(), has_attachments) if html else ("", has_attachments)
                )
        else:
            text = str(
                message.get_payload(decode=True),
                message.get_content_charset(),
                "ignore",
            ).encode("utf8", "replace")
            return text.strip(), has_attachments

    @imap_connection
    def _search_message(self, criterion: str) -> list:
        return self.imap_conn.search(None, "(" + criterion + ")")

    def _search_and_return_mail_ids(self, criterion: str) -> list:
        _, data = self._search_message(criterion)
        mail_ids = bytes.decode(data[0])
        return mail_ids.split() if len(mail_ids) > 1 else []

    @imap_connection
    def _set_message_flag(
        self, mail_id: str = None, flag: str = None, unset: bool = False
    ):
        flag_type = "-FLAGS" if unset else "+FLAGS"
        # self.imap_conn.uid("STORE", mail_id, flag_type, f"({flag})")
        mail_uid = self._fetch_uid(mail_id)
        status_code, data = self.imap_conn.uid("STORE", mail_uid, flag_type, flag)
        data_message = data[0]
        self.logger.debug("Set message flag: %s, %s", status_code, data)
        if status_code != "OK":
            self.logger.debug(
                "Message flag '%s' failed for mail_id: %s, mail_uid: %s",
                flag,
                mail_id,
                mail_uid,
            )
        return status_code == "OK" and data_message is not None

    @imap_connection
    def _delete_messages(self, mail_ids: list) -> None:
        for mail_id in mail_ids:
            self._set_message_flag(mail_id, FLAG_DELETED)
        self.imap_conn.expunge()

    @imap_connection
    def delete_message(self, criterion: str = "") -> bool:
        """Delete single message from server based on criterion.

        :param criterion: filter messages based on this, defaults to ""
        :return: True if success, False if not

        If criterion does not return exactly 1 message then delete is not done.

        Example:

        .. code-block:: robotframework

            Delete Message  SUBJECT \"Greetings RPA developer\"
        """
        self._validate_criterion(criterion)
        _, data = self._search_message(criterion)
        mail_ids = data[0].split()
        if len(mail_ids) != 1:
            self.logger.warning(
                "Delete message criteria matched %d messages. Not deleting.",
                len(mail_ids),
            )
            return False
        else:
            self._delete_messages(mail_ids)
            return True

    @imap_connection
    def delete_messages(self, criterion: str = "") -> bool:
        """Delete messages from server based on criterion.

        :param criterion: filter messages based on this, defaults to ""
        :return: True if success, False if not

        Example:

        .. code-block:: robotframework

            Delete Messages  SUBJECT Greetings
        """
        self._validate_criterion(criterion)
        mail_ids = self._search_and_return_mail_ids(criterion)
        self._delete_messages(mail_ids)
        return True

    @imap_connection
    def save_messages(self, criterion: str = "", target_folder: str = None) -> bool:
        # pylint: disable=C0301
        """Save messages based on criteria and store them to target folder
        with attachment files.

        Does not save message if `target_folder` is not given.

        :param criterion: filter messages based on this, defaults to ""
        :param target_folder: path to folder where message are saved, defaults to None
        :return: True if success, False if not

        Example:

        .. code-block:: robotframework

            Save Messages  SUBJECT Important message  target_folder=${USERDIR}${/}messages
        """  # noqa: E501
        self._validate_criterion(criterion)
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

    @imap_connection
    def list_messages(self, criterion: str = "") -> Any:
        """Return list of messages matching criterion.

        :param criterion: list emails matching this, defaults to ""
        :return: list of messages or False

        Example:

        .. code-block:: robotframework

            @{emails}  List Messages  SUBJECT \"rpa task\"
            FOR  ${email}  IN  @{EMAILS}
                Log  ${email}[Subject]
                Log  ${email}[From]
                Log  ${email}[Date]
                Log  ${email}[Delivered-To]
                Log  ${email}[Received]
                Log  ${email}[Has-Attachments]
            END
        """
        self.logger.info("List messages: %s", criterion)
        _, data = self._search_message(criterion)
        mail_ids = data[0].split()
        return self._fetch_messages(mail_ids)

    @imap_connection
    def save_attachments(
        self, criterion: str = "", target_folder: str = None, overwrite: bool = False
    ) -> Any:
        # pylint: disable=C0301
        """Save mail attachments into local folder.

        :param criterion: attachments are saved for mails matching this, defaults to ""
        :param target_folder: local folder for saving attachments to (needs to exist),
            defaults to user's home directory if None
        :param overwrite: overwrite existing file is True, defaults to False
        :return: list of saved attachments or False

        Example:

        .. code-block:: robotframework

            ${numsaved}  Save Attachments   SUBJECT \"rpa task\"
            ...          target_folder=${CURDIR}${/}messages  overwrite=True
        """  # noqa: E501
        attachments_saved = []
        messages = self.list_messages(criterion)
        for msg in messages:
            attachments_saved.append(
                self.save_attachment(msg, target_folder, overwrite)
            )
        return attachments_saved if len(attachments_saved) > 0 else False

    def save_attachment(self, message, target_folder, overwrite):
        # pylint: disable=C0301
        """Save mail attachment into local folder

        :param message: message item
        :param target_folder: local folder for saving attachments to (needs to exist),
            defaults to user's home directory if None
        :param overwrite: overwrite existing file is True, defaults to False

        Example:

        .. code-block:: robotframework

            @{emails}  List Messages  SUBJECT \"rpa task\"
            FOR  ${email}  IN  @{EMAILS}
                Run Keyword If   ${email}[Has-Attachments] == True
                ...              Save Attachment  ${email}  target_folder=${CURDIR}  overwrite=True
            END
        """  # noqa: E501
        if target_folder is None:
            target_folder = os.path.expanduser("~")
        msg = message["Message"] if isinstance(message, dict) else message
        attachments_saved = []
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

    @imap_connection
    def wait_for_message(
        self, criterion: str = "", timeout: float = 5.0, interval: float = 1.0
    ) -> Any:
        """Wait for email matching `criterion` to arrive into mailbox.

        :param criterion: message filter to wait for, defaults to ""
        :param timeout: total time in seconds to wait for email, defaults to 5.0
        :param interval: time in seconds for new check, defaults to 1.0
        :return: list of messages or False

        Example:

        .. code-block:: robotframework

            @{emails}  Wait For Message  SUBJECT \"rpa task\"  timeout=300  interval=10
        """
        self._validate_criterion(criterion)
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

    def _parse_folders(self, folders):
        parsed_folders = []
        folder_regex = r'\((?P<flags>.*)\)."(?P<delimiter>.*)"."(?P<name>.*)".*'
        for f in folders:
            flags, delimiter, name = re.search(folder_regex, bytes.decode(f)).groups()

            parsed_folders.append(
                {"name": name, "flags": flags, "delimiter": delimiter}
            )
        return parsed_folders

    @imap_connection
    def get_folder_list(self, subdirectory: str = None, pattern: str = None) -> list:
        """Get list of folders on the server

        :param subdirectory: list subdirectories for this folder
        :param pattern: list folders matching this pattern
        :return: list of folders

        Example:

        .. code-block:: robotframework

            @{folders}  Get Folder List
            @{folders}  Get Folder List  pattern=important
            @{folders}  Get Folder List  subdirectory=sub
        """
        self.logger.info("Get folder list")
        kwparams = {}
        if subdirectory:
            kwparams["directory"] = subdirectory
        if pattern:
            kwparams["pattern"] = pattern

        status_code, folders = self.imap_conn.list(**kwparams)
        if status_code == "OK":
            return self._parse_folders(folders)
        else:
            return []

    @imap_connection
    def select_folder(self, folder_name: str = "INBOX") -> int:
        """Select folder by name

        :param folder_name: name of the folder to select
        :return: message count in the selected folder

        Returns number of messages in the folder or
        exception if folder does not exist on the server.

        Example:

        .. code-block:: robotframework

            Select Folder   subfolder
        """
        self.logger.info("Select folder: %s", folder_name)
        status_code, data = self.imap_conn.select(mailbox=folder_name, readonly=False)
        if status_code == "OK":
            message_count = bytes.decode(data[0])
            return int(message_count)
        else:
            raise ValueError("Folder '%s' does not exist on the server" % folder_name)

    @imap_connection
    def rename_folder(
        self, oldname: str = None, newname: str = None, suppress_error: bool = False
    ) -> bool:
        """Rename email folder

        :param oldname: current folder name
        :param newname: new name for the folder
        :param suppress_error: to silence warning message, defaults to False
        :return: True if operation was successful, False if not

        Example:

        .. code-block:: robotframework

            Rename Folder   subfolder   filtered
        """
        if oldname is None or newname is None:
            raise KeyError(
                "Both 'oldname' and 'newname' and required for rename folder"
            )
        self.logger.info("Rename folder '%s' to '%s'", oldname, newname)
        status_code, data = self.imap_conn.rename(oldname, newname)

        if status_code == "OK":
            return True
        else:
            if suppress_error is False:
                self.logger.warning(
                    "Folder rename failed with message: '%s'",
                    bytes.decode(data[0]),
                )
            return False

    @imap_connection
    def delete_folder(self, folder_name: str = None) -> bool:
        """Delete email folder

        :param folder_name: current folder name
        :return: True if operation was successful, False if not

        Example:

        .. code-block:: robotframework

            Delete Folder   filtered
        """
        if folder_name is None:
            raise KeyError("'folder_name' is required for delete folder")
        self.logger.info("Delete folder '%s'", folder_name)
        status_code, data = self.imap_conn.delete(folder_name)
        if status_code == "OK":
            return True
        else:
            self.logger.warning(
                "Delete folder '%s' response status: '%s %s'",
                folder_name,
                status_code,
                bytes.decode(data[0]),
            )
            return False

    @imap_connection
    def create_folder(self, folder_name: str = None) -> bool:
        """Create email folder

        :param folder_name: name for the new folder
        :return: True if operation was successful, False if not

        Example:

        .. code-block:: robotframework

            Create Folder   filtered
        """
        if folder_name is None:
            raise KeyError("'folder_name' is required for create folder")
        self.logger.info("Create folder '%s'", folder_name)
        status_code, data = self.imap_conn.create(folder_name)
        if status_code == "OK":
            return True
        else:
            self.logger.warning(
                "Create folder '%s' response status: '%s %s'",
                folder_name,
                status_code,
                bytes.decode(data[0]),
            )
            return False

    @imap_connection
    def flag_messages(self, criterion: str = None, unflag: bool = False) -> Any:
        """Mark messages as `flagged`

        :param criterion: mark messages matching criterion
        :param unflag: to mark messages as not `flagged`
        :return: successful operations (int), matching messages (int)

        Example:

        .. code-block:: robotframework

            ${flagged}  ${oftotal}    Flag Messages   SUBJECT rpa
            ${unflagged}  ${oftotal}  Flag Messages   SUBJECT rpa  unflag=True
        """
        self._validate_criterion(criterion)
        if unflag:
            self.logger.info("Unflag messages: '%s'", criterion)
        else:
            self.logger.info("Flag messages: '%s'", criterion)
        mail_ids = self._search_and_return_mail_ids(criterion)
        success_count = 0
        for mail_id in mail_ids:
            status = self._set_message_flag(mail_id, FLAG_FLAGGED, unflag)
            success_count += 1 if status else 0
        return success_count, len(mail_ids)

    @imap_connection
    def unflag_messages(self, criterion: str = None) -> Any:
        """Mark messages as not `flagged`

        :param criterion: mark messages matching criterion
        :return: successful operations (int), matching messages (int)

        Example:

        .. code-block:: robotframework

            ${unflagged}  ${oftotal}  Unflag Messages   SUBJECT rpa
        """
        return self.flag_messages(criterion, unflag=True)

    @imap_connection
    def mark_as_read(self, criterion: str = None, unread: bool = False) -> Any:
        """Mark messages as `read`

        :param criterion: mark messages matching criterion
        :param unread: to mark messages as not `read`
        :return: successful operations (int), matching messages (int)

        Example:

        .. code-block:: robotframework

            ${read}  ${oftotal}  Mark As Read   SUBJECT rpa
        """
        self._validate_criterion(criterion)
        if unread:
            self.logger.info("Mark messages as unread: '%s'", criterion)
        else:
            self.logger.info("Mark messages as read: '%s'", criterion)
        mail_ids = self._search_and_return_mail_ids(criterion)
        success_count = 0
        for mail_id in mail_ids:
            status = self._set_message_flag(mail_id, FLAG_SEEN, unread)
            success_count += 1 if status else 0
        return success_count, len(mail_ids)

    @imap_connection
    def mark_as_unread(self, criterion: str = None) -> Any:
        """Mark messages as not `read`

        :param criterion: mark messages matching criterion
        :return: successful operations (int), matching messages (int)

        Example:

        .. code-block:: robotframework

            ${unread}  ${oftotal}  Mark As Unread   SUBJECT rpa
        """
        return self.mark_as_read(criterion, unread=True)

    def _validate_criterion(self, criterion: str) -> bool:
        if criterion is None or len(criterion) < 1:
            raise KeyError("Criterion is required parameter")

    def _fetch_uid(self, mail_id):
        _, data = self.imap_conn.fetch(mail_id, "(UID)")
        pattern_uid = re.compile(r"\d+ \(UID (?P<uid>\d+)\)")
        match = pattern_uid.match(bytes.decode(data[0]))
        return match.group("uid")
