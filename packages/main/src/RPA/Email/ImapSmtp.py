import base64
from enum import Enum
from functools import wraps

from io import StringIO
import logging
import os
import re
import time

# email package declares these properties in the __all__ definition but
# pylint ignores that
from email import encoders, message_from_bytes  # pylint: disable=E0611
from email.message import Message  # pylint: disable=E0611
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

from typing import Any, List, Union

from robot.libraries.BuiltIn import BuiltIn, RobotNotRunningError
from RPA.RobotLogListener import RobotLogListener


class Action(Enum):
    """Possible email actions."""

    msg_copy = 1
    msg_delete = 2
    msg_list = 3
    msg_flag = 4
    msg_unflag = 5
    msg_read = 6
    msg_unread = 7
    msg_save = 8
    msg_attachment_save = 9
    msg_move = 10
    glabel_add = 20  # Add GMail label
    glabel_remove = 21  # Remove GMail label


def to_action(value):
    """Convert value to Action enum."""
    if isinstance(value, Action):
        return value

    sanitized = str(value).lower().strip().replace(" ", "_")
    try:
        return Action[sanitized]
    except KeyError as err:
        raise ValueError(f"Unknown email action: {value}") from err


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

    ***About criteria argument***

    Various keywords like ``List Messages`` and ``Move Messages`` have keyword
    argument called ``criterion`` which can be used to filter emails according
    to given criteria.

    Syntax needs to according to specification and more information about that
    can be read from https://robocorp.com/docs/development-guide/email/sending-emails-with-gmail-smtp#listing-email-messages-by-criteria

    **Troubleshooting**

    - Authentication error with Gmail - "Application-specific password required"
        see. https://support.google.com/mail/answer/185833?hl=en

    **Examples**

    **Robot Framework**

    It is highly recommended to secure your passwords and take care
    that they are not stored in version control by mistake.
    See ``RPA.Robocorp.Vault`` to see how to store secrets in
    Robocorp Vault.

    When sending HTML content with IMG tags, the ``src`` filenames must match
    the base image name given with the ``images`` parameter.

    .. code-block:: robotframework

        *** Settings ***
        Library     RPA.Email.ImapSmtp   smtp_server=smtp.gmail.com  smtp_port=587
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

        mail = ImapSmtp(smtp_server="smtp.gmail.com", smtp_port=587)
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
        encoding: str = "utf-8",
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
        self.selected_folder = None
        self.encoding = encoding

    def __del__(self) -> None:
        if self.smtp_conn:
            try:
                self.smtp_conn.quit()
            except SMTPServerDisconnected:
                self.logger.debug("Was already disconnected")
            finally:
                self.smtp_conn = None

        if self.imap_conn:
            try:
                self.imap_conn.close()
                self.imap_conn.logout()
            except Exception:  # pylint: disable=W0703
                pass
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

        self.account = account
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
        account = account or self.account
        password = password or self.password
        smtp_server = smtp_server or self.smtp_server
        smtp_port = smtp_port or self.smtp_port
        if smtp_server:
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
            if account and password:
                self.smtp_conn.login(account, password)
        else:
            self.logger.warning("SMTP server address is needed for authentication")
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
            ...           attachments=${CURDIR}${/}report.pdf
        """
        add_charset(self.encoding, QP, QP, self.encoding)
        recipients, attachments, images = self._handle_message_parameters(
            recipients, attachments, images
        )
        msg = MIMEMultipart()

        self._add_attachments_to_msg(attachments, msg)

        msg["From"] = sender
        msg["To"] = ",".join(recipients)
        msg["Subject"] = Header(subject, self.encoding)

        if html:
            for im in images:
                im = im.strip()
                imname = Path(im).name
                body = body.replace(str(imname), f"cid:{imname}")
                with open(im, "rb") as f:
                    img = MIMEImage(f.read())
                    img.add_header("Content-ID", f"<{imname}>")
                    msg.attach(img)
            htmlpart = MIMEText(body, "html", self.encoding)
            msg.attach(htmlpart)
        else:
            textpart = MIMEText(body, "plain", self.encoding)
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
            if self.smtp_conn is None:
                self.authorize_smtp()
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
                        "attachment",
                        filename=Path(filename).name,
                    )
                    msg.attach(part)

    @imap_connection
    def _fetch_messages(self, mail_ids: list) -> list:
        messages = []
        for mail_id in mail_ids:
            _, data = self.imap_conn.fetch(mail_id, "(RFC822)")
            if data[0] is None:
                self.logger.debug("Data was none for : %s", mail_id)
                continue
            message = message_from_bytes(data[0][1])
            message_dict = {"Mail-Id": mail_id, "Message": message}
            for k, v in message.items():
                msg_item = decode_header(v)
                message_dict[k] = make_header(msg_item)
            message_dict["Body"], has_attachments = self.get_decoded_email_body(message)
            message_dict["Has-Attachments"] = has_attachments
            messages.append(message_dict)
        return messages

    def get_decoded_email_body(self, message):
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
                    text = str(part.get_payload(decode=True), str(charset), "ignore")
                if part.get_content_type() == "text/html":
                    html = str(part.get_payload(decode=True), str(charset), "ignore")

            if text:
                return (
                    (text.strip(), has_attachments) if text else ("", has_attachments)
                )
            else:
                return (
                    (html.strip(), has_attachments) if html else ("", has_attachments)
                )
        else:
            content_charset = message.get_content_charset()
            text = str(
                message.get_payload(decode=True),
                content_charset or self.encoding,
                "ignore",
            )
            return text.strip(), has_attachments

    @imap_connection
    def _do_actions_on_messages(
        self,
        criterion: str,
        actions: list,
        labels: str = None,
        source_folder: str = None,
        target_folder: str = None,
        limit: int = None,
        overwrite: bool = False,
        readonly: bool = False,
    ) -> list:
        selected_folder = source_folder or self.selected_folder
        folders = self.get_folder_list(subdirectory=selected_folder)
        result = {"actions_done": 0, "message_count": 0, "ids": [], "uids": {}}

        if source_folder:
            for f in folders:
                if "Noselect" in f["flags"]:
                    continue
                self.select_folder(f["name"], readonly)
                self._search_message(criterion, actions, limit, result)
        else:
            self._search_message(criterion, actions, limit, result)

        if len(result["uids"].keys()) == 0:
            self.logger.warning(
                "Can't find any messages matching criterion '%s' in source folder '%s'",
                criterion,
                source_folder or "INBOX",
            )
            return result
        if limit is None or len(result["uids"].keys()) <= limit:
            for mail in result["uids"].items():
                status = self._perform_actions(
                    actions,
                    mail,
                    labels=labels,
                    target_folder=target_folder,
                    overwrite=overwrite,
                )
                if status:
                    result["actions_done"] += 1
        else:
            self.logger.warning(
                "Some emails were not processed because limit was reached"
            )
        return result

    def _search_message(self, criterion, actions, limit, result):
        search_encoding = None
        search_command = None
        literal_search = criterion.startswith("literal:")
        gmail_search = criterion.startswith("gmail:")

        if literal_search:
            search_encoding = "utf-8"
            search_term = criterion.replace("literal:", "")
            search_command, search_literal = search_term.split(" ", 1)

            self.imap_conn.literal = b"%s" % search_literal.encode("utf-8")
        elif gmail_search:
            search_encoding = "utf-8"
            search_command = "X-GM-RAW"
            self.imap_conn.literal = b"(%s)" % criterion.replace("gmail:", "").encode(
                "utf-8"
            )
        else:
            search_command = "(%s)" % criterion
        try:
            self.logger.info("IMAP search: '%s'", criterion)
            status, data = self.imap_conn.search(search_encoding, search_command)
        except Exception as err:  # pylint: disable=broad-except
            self.logger.warning(
                "Email search returned: %s (%s)", str(err), search_command
            )
            return False
        if status == "OK":
            mail_id_data = bytes.decode(data[0])
            mail_ids = mail_id_data.split() if len(mail_id_data) > 0 else []
            if limit and len(mail_ids) + result["message_count"] > limit:
                return True
            if len(mail_ids) > 0:
                result["message_count"] += len(mail_ids)
                result["ids"].extend(mail_ids)
                for mail_id in mail_ids:
                    mail_uid, message = self._fetch_uid_and_body(mail_id, actions)
                    if mail_uid is None or mail_uid in result["uids"].keys():
                        continue
                    message["uid"] = mail_uid
                    result["uids"][mail_uid] = message
            return True
        else:
            self.logger.warning("Search result not OK: %s", status)
            return False

    def _perform_actions(
        self,
        actions: list,
        mail: dict,
        labels: str = None,
        target_folder: str = None,
        overwrite: bool = False,
    ):
        action_status = True
        mail_uid, mail_dict = mail

        store_params = {
            Action.glabel_add: ["+X-GM-LABELS", f"({labels})"],
            Action.glabel_remove: ["-X-GM-LABELS", f"({labels})"],
            Action.msg_delete: ["+FLAGS", FLAG_DELETED],
            Action.msg_flag: ["+FLAGS", FLAG_FLAGGED],
            Action.msg_unflag: ["-FLAGS", FLAG_FLAGGED],
            Action.msg_read: ["+FLAGS", FLAG_SEEN],
            Action.msg_unread: ["-FLAGS", FLAG_SEEN],
        }

        for act in actions:
            action = to_action(act)
            if action == Action.msg_list:
                continue
            if action in store_params.keys():
                m_op, m_param = store_params[action]
                action_status, _ = self.imap_conn.uid("STORE", mail_uid, m_op, m_param)
                self.logger.debug(
                    "STORE %s %s %s RESULT %s", mail_uid, m_op, m_param, action_status
                )
            elif action == Action.msg_copy:
                action_status, _ = self.imap_conn.uid("COPY", mail_uid, target_folder)
                self.logger.debug(
                    "COPY %s %s RESULT %s", mail_uid, target_folder, action_status
                )
            elif action == Action.msg_move:
                action_status, _ = self.imap_conn.uid("COPY", mail_uid, target_folder)
                m_op, m_param = store_params[Action.msg_delete]
                action_status, _ = self.imap_conn.uid("STORE", mail_uid, m_op, m_param)
            elif action == Action.msg_save:
                if target_folder is None:
                    target_folder = os.path.expanduser("~")
                self._save_eml_file(mail_dict, target_folder, overwrite)
            elif action == Action.msg_attachment_save:
                if target_folder is None:
                    target_folder = os.path.expanduser("~")
                self._save_attachment(mail_dict, target_folder, overwrite)
            else:
                # TODO: mypy should handle enum exhaustivity validation
                raise ValueError(f"Unsupported email action: {action}")
        return action_status

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
        result = self._do_actions_on_messages(
            criterion, actions=[Action.msg_delete], limit=1
        )
        return result["actions_done"] == 1

    @imap_connection
    def delete_messages(self, criterion: str = "", limit: int = None) -> bool:
        """Delete messages from server based on criterion.

        :param criterion: filter messages based on this, defaults to ""
        :param limit: maximum number of message to delete
        :return: True if success, False if not

        Example:

        .. code-block:: robotframework

            Delete Messages  SUBJECT Greetings
        """
        self._validate_criterion(criterion)
        result = self._do_actions_on_messages(
            criterion, actions=[Action.msg_delete], limit=limit
        )
        return (
            result["actions_done"] > 0
            and result["actions_done"] == result["message_count"]
        )

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
        result = self._do_actions_on_messages(
            criterion, actions=[Action.msg_save], target_folder=target_folder
        )
        return (
            result["actions_done"] > 0
            and result["actions_done"] == result["message_count"]
        )

    @imap_connection
    def list_messages(
        self, criterion: str = "", source_folder: str = None, readonly: bool = True
    ) -> Any:
        """Return list of messages matching criterion.

        :param criterion: list emails matching this, defaults to ""
        :param source_folder: list messages from this folder
        :param readonly: set False if you want to mark matching messages as read
        :return: list of messages

        *Note.* listing messages without `source_folder` might take a long time

        Example:

        .. code-block:: robotframework

            @{emails}  List Messages  SUBJECT "rpa task"
            FOR  ${email}  IN  @{EMAILS}
                Log  ${email}[Subject]
                Log  ${email}[From]
                Log  ${email}[Date]
                Log  ${email}[Delivered-To]
                Log  ${email}[Received]
                Log  ${email}[Has-Attachments]
                Log  ${email}[uid]
            END
        """
        result = self._do_actions_on_messages(
            criterion,
            source_folder=source_folder,
            actions=[Action.msg_list],
            readonly=readonly,
        )
        values = result["uids"].values()
        converted = []
        for v in values:
            if v:
                converted.append(
                    {
                        str(key): value
                        if isinstance(value, (str, bool, int, Message))
                        else str(value)
                        for key, value in v.items()
                    }
                )
        return converted

    @imap_connection
    def save_attachments(
        self, criterion: str = "", target_folder: str = None, overwrite: bool = False
    ) -> List:
        # pylint: disable=C0301
        """Save mail attachments of emails matching criterion into local folder.

        :param criterion: attachments are saved for mails matching this, defaults to ""
        :param target_folder: local folder for saving attachments to (needs to exist),
            defaults to user's home directory if None
        :param overwrite: overwrite existing file is True, defaults to False
        :return: list of saved attachments

        Example:

        .. code-block:: robotframework

            ${numsaved}  Save Attachments   SUBJECT "rpa task"
            ...          target_folder=${CURDIR}${/}messages  overwrite=True
        """  # noqa: E501
        attachments_saved = []
        messages = self.list_messages(criterion)
        for msg in messages:
            attachments_saved.extend(
                self.save_attachment(msg, target_folder, overwrite)
            )
        return attachments_saved

    def save_attachment(
        self, message: Union[dict, Message], target_folder: str, overwrite: bool
    ):
        # pylint: disable=C0301
        """Save mail attachment of single given email into local folder

        :param message: message item
        :param target_folder: local folder for saving attachments to (needs to exist),
            defaults to user's home directory if None
        :param overwrite: overwrite existing file is True, defaults to False

        Example:

        .. code-block:: robotframework

            @{emails}  List Messages  SUBJECT "rpa task"
            FOR  ${email}  IN  @{emails}
                Run Keyword If   ${email}[Has-Attachments] == True
                ...              Save Attachment  ${email}  target_folder=${CURDIR}  overwrite=True
            END
        """  # noqa: E501
        if target_folder is None:
            target_folder = os.path.expanduser("~")
        return self._save_attachment(message, target_folder, overwrite)

    def _save_attachment(self, message, target_folder, overwrite):
        attachments_saved = []
        msg = message["Message"] if isinstance(message, dict) else message
        for part in msg.walk():
            content_maintype = part.get_content_maintype()
            content_disposition = part.get("Content-Disposition")
            self.logger.info(
                "Email attachment content-type: '%s' and content-disposition: '%s'",
                content_maintype,
                content_disposition,
            )
            if content_maintype != "multipart" and content_disposition is not None:
                filename = part.get_filename().replace("\r", "").replace("\n", "")
                self.logger.info("Attachment filename: '%s'", filename)
                if filename:
                    transfer_encoding = part.get_all("Content-Transfer-Encoding")
                    if transfer_encoding and transfer_encoding[0] == "base64":
                        filename_parts = filename.split("?")
                        if len(filename_parts) > 1:
                            filename = base64.b64decode(filename_parts[3]).decode(
                                filename_parts[1]
                            )
                    filepath = Path(target_folder) / Path(filename).name
                    self.logger.info("Attachment filepath: '%s'", filepath)
                    if not filepath.exists() or overwrite:
                        payload = part.get_payload(decode=True)
                        if payload:
                            self.logger.info(
                                "Saving attachment: %s",
                                filename,
                            )
                            with open(filepath, "wb") as f:
                                f.write(payload)
                                attachments_saved.append(str(filepath))
                        else:
                            self.logger.debug(
                                "Attachment '%s' did not have payload to write",
                                filename,
                            )
                    elif filepath.exists() and not overwrite:
                        self.logger.warning("Did not overwrite file: %s", filepath)
        return attachments_saved

    def _save_eml_file(self, message, target_folder, overwrite):
        emlfile = Path(target_folder) / f"{message['Mail-Id']}.eml"
        if not emlfile.exists() or overwrite:
            with open(emlfile, "wb") as f:
                f.write(message["bytes"])
        elif emlfile.exists() and not overwrite:
            self.logger.warning("Did not overwrite file: %s", emlfile)

    @imap_connection
    def wait_for_message(
        self,
        criterion: str = "",
        timeout: float = 5.0,
        interval: float = 1.0,
        readonly: bool = True,
    ) -> Any:
        """Wait for email matching `criterion` to arrive into mailbox.

        :param criterion: message filter to wait for, defaults to ""
        :param timeout: total time in seconds to wait for email, defaults to 5.0
        :param interval: time in seconds for new check, defaults to 1.0
        :param readonly: set False if you want to mark matching messages as read
        :return: list of messages

        Example:

        .. code-block:: robotframework

            @{emails}  Wait For Message  SUBJECT \"rpa task\"  timeout=300  interval=10
        """
        self._validate_criterion(criterion)
        end_time = time.time() + float(timeout)
        while time.time() < end_time:
            self.imap_conn.select("inbox", readonly)
            result = self._do_actions_on_messages(
                criterion,
                actions=[Action.msg_list],
                source_folder="INBOX",
                readonly=readonly,
            )
            if result["message_count"] > 0:
                return result["uids"].values()
            time.sleep(interval)
        return []

    def _parse_folders(self, folders):
        if folders and len(folders) == 1 and folders[0] is None:
            return []
        parsed_folders = []
        folder_regex = r'\((?P<flags>.*)\)\s"(?P<delimiter>.*)"\s"?(?P<name>[^"]*)"?'
        for f in folders:
            match = re.search(folder_regex, bytes.decode(f))
            if not match:
                self.logger.warning("Cannot parse folder name %s", bytes.decode(f))
                continue
            parsed_folders.append(match.groupdict())
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
        kwparams = {}
        if subdirectory:
            kwparams["directory"] = subdirectory
        if pattern:
            kwparams["pattern"] = pattern

        status_code, folders = self.imap_conn.list(**kwparams)

        if status_code == "OK":
            parsed_folders = self._parse_folders(folders)
            return [
                f
                for f in parsed_folders
                if subdirectory is None or subdirectory == f["name"]
            ]
        else:
            return []

    @imap_connection
    def select_folder(self, folder_name: str = "INBOX", readonly: bool = False) -> int:
        """Select folder by name

        :param folder_name: name of the folder to select
        :param readonly: if set to True then message flags are not modified
        :return: message count in the selected folder

        Returns number of messages in the folder or
        exception if folder does not exist on the server.

        Example:

        .. code-block:: robotframework

            Select Folder   subfolder
        """
        status_code, data = self.imap_conn.select(
            mailbox=f'"{folder_name}"', readonly=readonly
        )
        if status_code == "OK":
            message_count = bytes.decode(data[0])
            self.selected_folder = folder_name
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
        action = Action.msg_unflag if unflag else Action.msg_flag
        result = self._do_actions_on_messages(criterion, actions=[action])
        return (
            result["actions_done"] > 0
            and result["actions_done"] == result["message_count"]
        )

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
        action = Action.msg_unread if unread else Action.msg_read
        result = self._do_actions_on_messages(criterion, actions=[action])
        return (
            result["actions_done"] > 0
            and result["actions_done"] == result["message_count"]
        )

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

    def _fetch_uid_and_body(self, mail_id, actions):
        body = None
        _, data = self.imap_conn.fetch(mail_id, "(UID RFC822)")
        pattern_uid = re.compile(r".*UID (\d+) RFC822")
        decoded_data = bytes.decode(data[0][0]) if data[0] else None
        match_result = pattern_uid.match(decoded_data) if decoded_data else None
        uid = match_result.group(1) if match_result else None
        if uid:
            body = self._fetch_body(mail_id, data, actions)

        key_to_change = None
        message_id_to_add = None
        for key, val in body.items():
            if key.lower() == "message-id":
                key_to_change = key
                message_id_to_add = str(val).replace("<", "").replace(">", "").strip()
        if key_to_change:
            body["Message-ID"] = message_id_to_add
            if key_to_change != "Message-ID":
                del body[key_to_change]
        return uid, body

    def _fetch_body(self, mail_id, data, actions):
        # _, data = self.imap_conn.fetch(mail_id, "(RFC822)")
        message = message_from_bytes(data[0][1])
        message_dict = {"Mail-Id": mail_id, "Message": message}
        if Action.msg_save in actions:
            message_dict["bytes"] = data[0][1]
        for k, v in message.items():
            msg_item = decode_header(v)
            message_dict[k] = make_header(msg_item)
        (
            message_dict["Body"],
            has_attachments,
        ) = self.get_decoded_email_body(message)
        # SET DEFAULT VALUES FOR KEYS
        if "Delivered-To" not in message_dict.keys():
            message_dict["Delivered-To"] = ""
        message_dict["Has-Attachments"] = has_attachments
        return message_dict

    @imap_connection
    def move_messages(
        self,
        criterion: str = None,
        target_folder: str = None,
        source_folder: str = None,
    ) -> bool:
        """Move messages from source folder to target folder

        :param criterion: move messages matching criterion
        :param source_folder: location of the messages, default `INBOX`
        :param target_folder: where messages should be move into
        :return: True if all move operations succeeded, False if not
        Example:

        .. code-block:: robotframework

            ${result}=    Move Messages
            ...    criterion=SUBJECT "order confirmation 32"
            ...    target_folder=yyy

            ${result}=    Move Messages
            ...    criterion=ALL
            ...    source_folder=yyy
            ...    target_folder=XXX
        """
        self._validate_criterion(criterion)
        if target_folder is None or len(target_folder) == 0:
            raise KeyError("Can't move messages without target_folder")
        result = self._do_actions_on_messages(
            criterion=criterion,
            actions=[Action.msg_move],
            source_folder=source_folder,
            target_folder=target_folder,
        )
        if result["actions_done"] > 0:
            self.imap_conn.expunge()
        action_mismatch = result["actions_done"] != result["message_count"]
        if action_mismatch:
            self.logger.warning(
                "Criterion matched %s messages, but actions done to %s messages",
                result["message_count"],
                result["actions_done"],
            )
        return (
            result["actions_done"] > 0
            and result["actions_done"] == result["message_count"]
        )

    @imap_connection
    def move_messages_by_ids(
        self,
        message_ids: Union[str, List],
        target_folder: str,
        source_folder: str,
        use_gmail_search: bool = False,
    ) -> bool:
        """Move message by their Message-ID's from source folder to target folder

        :param message_ids: one Message-ID as string or list of Message-IDs
        :param source_folder: location of the messages, default `INBOX`
        :param target_folder: where messages should be move into
        :param use_gmail_search: set to True to use `Rfc822msgid` search, default
            is `HEADER Message-ID` search
        :return: True if all move operations succeeded, False if not
        """
        if not message_ids:
            self.logger.warning("No message ids given for Move Messages By IDs")
            return False
        idlist = message_ids if isinstance(message_ids, list) else [message_ids]
        results = []
        for mid in idlist:
            if use_gmail_search:
                move_criterion = f"gmail:Rfc822msgid:{mid}"
            else:
                move_criterion = f"HEADER Message-ID {mid}"
            result = self.move_messages(
                criterion=move_criterion,
                source_folder=source_folder,
                target_folder=target_folder,
            )
            if not result:
                self.logger.warning("Moving Message-ID '%s' failed", mid)
            results.append(result)
        return all(results)

    @imap_connection
    def _modify_gmail_labels(
        self,
        labels: str,
        criterion: str,
        action: bool = True,
        source_folder: str = None,
    ) -> bool:
        result = self._do_actions_on_messages(
            criterion=criterion,
            actions=[action],
            labels=labels,
            source_folder=source_folder,
        )

        return (
            result["actions_done"] > 0
            and result["actions_done"] == result["message_count"]
        )

    @imap_connection
    def add_gmail_labels(self, labels, criterion, source_folder: str = None) -> bool:
        """Add GMail labels to messages matching criterion and if given,
        source folder

        :param labels: comma separated list of labels to add
        :param criterion: label messages matching criterion
        :param source_folder: look for messages in this folder, default all folders
        :return: status of the operation

        Example:

        .. code-block:: robotframework

            Add Gmail Labels  customer1   SUBJECT "order confirmation"
            Add Gmail Labels  wip         SUBJECT "order confirmation"   customerfolder
        """
        return self._modify_gmail_labels(
            labels, criterion, Action.glabel_add, source_folder
        )

    @imap_connection
    def remove_gmail_labels(self, labels, criterion, source_folder: str = None) -> bool:
        """Remove GMail labels to messages matching criterion and if given,
        source folder

        :param labels: comma separated list of labels to remove
        :param criterion: unlabel messages matching criterion
        :param source_folder: look for messages in this folder, default all folders
        :return: status of the operation

        Example:

        .. code-block:: robotframework

            Remove Gmail Labels  wip  SUBJECT "order confirmation"
            Remove Gmail Labels  wip  SUBJECT "order confirmation"  customerfolder
        """
        return self._modify_gmail_labels(
            labels, criterion, Action.glabel_remove, source_folder
        )

    @imap_connection
    def do_message_actions(
        self,
        criterion: str = "",
        actions: list = None,
        source_folder: str = None,
        target_folder: str = None,
        labels: str = None,
        limit: int = None,
        overwrite: bool = False,
    ) -> Any:
        """Do actions to messages matching criterion and if given,
        source folder

        Actions can be:

        - msg_copy
        - msg_delete
        - msg_flag
        - msg_unflag
        - msg_read
        - msg_unread
        - msg_save
        - msg_attachment_save
        - glabel_add
        - glabel_remove

        Result object contains following attributes:

        - actions_done, number of messages on which action was performed
        - message_count, number of messages matching criterion
        - ids, message ids matching criterion
        - uids, dictionary of message uids and message content

        :param criterion: perform actions on messages matching this
        :param actions: list of actions to perform on matching messages
        :param source_folder: look for messages in this folder, default all folders
        :param target_folder: can be file path or email folder
         (for example action: msg_copy)
        :param labels: comma separated list of labels (for example action: glabel_add)
        :param limit:  maximum number of messages (for example action: msg_delete)
        :param overwrite: to control if file should overwrite
         (for example action: msg_attachment_save)
        :return: result object

        Example:

        .. code-block:: robotframework

            ${actions}=   Create List  msg_unflag  msg_read  msg_save  msg_attachment_save
            Do Message Actions    SUBJECT "Order confirmation"
            ...                   ${actions}
            ...                   source_folder=XXX
            ...                   target_folder=${CURDIR}
            ...                   overwrite=True
        """  # noqa: E501

        parsed_actions = [to_action(act) for act in actions]
        result = self._do_actions_on_messages(
            criterion=criterion,
            actions=parsed_actions,
            labels=labels,
            source_folder=source_folder,
            target_folder=target_folder,
            limit=limit,
            overwrite=overwrite,
        )
        return (
            result["actions_done"] > 0
            and result["actions_done"] == result["message_count"]
        )
