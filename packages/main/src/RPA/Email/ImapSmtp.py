import base64
import logging
import os
import re
import time

# email package declares these properties in the __all__ definition but
# pylint ignores that
from email import encoders, message_from_bytes  # pylint: disable=E0611
from email.charset import QP, add_charset  # pylint: disable=E0611
from email.generator import Generator  # pylint: disable=E0611
from email.header import Header, decode_header, make_header  # pylint: disable=E0611
from email.message import Message  # pylint: disable=E0611
from email.mime.base import MIMEBase  # pylint: disable=E0611
from email.mime.image import MIMEImage  # pylint: disable=E0611
from email.mime.multipart import MIMEMultipart  # pylint: disable=E0611
from email.mime.text import MIMEText  # pylint: disable=E0611
from enum import Enum
from functools import wraps
from imaplib import IMAP4_SSL
from io import StringIO
from pathlib import Path
from smtplib import (
    SMTP,
    SMTP_SSL,
    SMTPConnectError,
    SMTPNotSupportedError,
    SMTPServerDisconnected,
    ssl,
)
from typing import Any, BinaryIO, List, Optional, Tuple, Union

from htmldocx import HtmlToDocx

from RPA.Email.common import (
    OAuthMixin,
    OAuthProvider,
    OAuthProviderType,
    counter_duplicate_path,
)
from RPA.Robocorp.utils import protect_keywords


FilePath = Union[str, Path]

IMAGE_FORMATS = ["jpg", "jpeg", "bmp", "png", "gif"]
FLAG_DELETED = "\\Deleted"
FLAG_SEEN = "\\Seen"
FLAG_FLAGGED = "\\Flagged"
FLAG_TRASH = "\\Trash"


class AttachmentPosition(Enum):
    """Possible attachment positions in the message content."""

    TOP = 1  # Default
    BOTTOM = 2


def to_attachment_position(value):
    """Convert value to AttachmentPosition enum."""
    if isinstance(value, AttachmentPosition):
        return value

    sanitized = str(value).upper().strip().replace(" ", "_")
    try:
        return AttachmentPosition[sanitized]
    except KeyError as err:
        raise ValueError(f"Unknown AttachmentPosition: {value}") from err


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
    msg_trash = 11
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


def get_part_filename(msg: Message) -> Optional[str]:
    filename = msg.get_filename()
    if not filename:
        return None

    decoded = decode_header(filename)
    if decoded[0][1] is not None:
        filename = decoded[0][0].decode(decoded[0][1])
    return filename.replace("\r", "").replace("\n", "")


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


class ImapSmtp(OAuthMixin):
    """`ImapSmtp` is a library for sending, reading, and deleting emails.
    `ImapSmtp` is interfacing with SMTP and IMAP protocols.

    ***About criteria argument***

    Various keywords like ``List Messages`` and ``Move Messages`` have keyword
    argument called ``criterion`` which can be used to filter emails according
    to given criteria.

    Syntax needs to according to specification and more information about that
    can be read from https://robocorp.com/docs/development-guide/email/sending-emails-with-gmail-smtp#listing-email-messages-by-criteria

    **Troubleshooting**

    - Authentication error with GMail - "Application-specific password required"
        See: https://support.google.com/mail/answer/185833?hl=en
    - More secure apps (XOAUTH2 protocol) - Use the OAuth2 flow as in this Portal robot:
        `example-oauth-email <https://github.com/robocorp/example-oauth-email>`_

        Make sure to specify a `provider` (and optionally a `tenant`) when importing
        the library and planning to use this flow.

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
        ${GMAIL_PASSWORD}       APP_PASSWORD
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
        gmail_password = "APP_PASSWORD"

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

    TO_PROTECT = [
        "authorize",
        "authorize_imap",
        "authorize_smtp",
        "set_credentials",
        "generate_oauth_string",
    ] + OAuthMixin.TO_PROTECT

    def __init__(
        self,
        smtp_server: Optional[str] = None,
        smtp_port: int = 587,
        imap_server: Optional[str] = None,
        imap_port: int = 993,
        account: Optional[str] = None,
        password: Optional[str] = None,
        encoding: str = "utf-8",
        provider: OAuthProviderType = OAuthProvider.GOOGLE,
        tenant: Optional[str] = None,
    ) -> None:
        # Init the OAuth2 support. (ready if used)
        super().__init__(provider, tenant=tenant)

        protect_keywords("RPA.Email.ImapSmtp", self.TO_PROTECT)
        self.logger = logging.getLogger(__name__)

        self.smtp_server = smtp_server
        self.imap_server = imap_server if imap_server else smtp_server
        self.smtp_port = int(smtp_port)
        self.imap_port = int(imap_port)
        self.encoding = encoding
        self.account = self.password = None
        self.set_credentials(account, password)

        self.smtp_conn = None
        self.imap_conn = None
        self.selected_folder = None

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

    def set_credentials(
        self, account: Optional[str] = None, password: Optional[str] = None
    ) -> None:
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
        is_oauth: bool = False,
    ) -> None:
        """Authorize to SMTP server.

        :param account: SMTP account name, defaults to None
        :param password: SMTP account password, defaults to None
        :param smtp_server: SMTP server address, defaults to None
        :param smtp_port: SMTP server port, defaults to None (587 for SMTP)
        :param is_oauth: Use XOAUTH2 protocol with a base64 encoded OAuth2 string as
            `password`

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
                if is_oauth:
                    self.smtp_conn.auth(
                        "XOAUTH2", lambda: base64.b64decode(password.encode()).decode()
                    )
                else:
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
        is_oauth: bool = False,
    ) -> None:
        """Authorize to IMAP server.

        :param account: IMAP account name, defaults to None
        :param password: IMAP account password, defaults to None
        :param imap_server: IMAP server address, defaults to None
        :param imap_port: IMAP server port, defaults to None
        :param is_oauth: Use XOAUTH2 protocol with a base64 encoded OAuth2 string as
            `password`

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
            if is_oauth:
                self.imap_conn.authenticate(
                    "XOAUTH2", lambda _: base64.b64decode(password.encode())
                )
            else:
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
        is_oauth: bool = False,
    ) -> None:
        # pylint: disable=C0301
        """Authorize user to SMTP and IMAP servers.

        :param account: user account as string, defaults to None
        :param password: user password as string, defaults to None
        :param smtp_server: SMTP server address, defaults to None
        :param imap_server: IMAP server address, defaults to None
        :param smtp_port: SMTP server port, defaults to None (587 for SMTP)
        :param imap_port: IMAP server port, defaults to None
        :param is_oauth: Use XOAUTH2 protocol with a base64 encoded OAuth2 string as
            `password`

        Will use separately set credentials or those given in keyword call.

        Example:

        .. code-block:: robotframework

            Authorize    ${username}   ${password}  smtp_server=smtp.gmail.com  smtp_port=587
        """  # noqa: E501
        self.authorize_smtp(
            account, password, smtp_server, smtp_port, is_oauth=is_oauth
        )
        self.authorize_imap(
            account, password, imap_server, imap_port, is_oauth=is_oauth
        )

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
        recipients: Union[List[str], str],
        subject: str = "",
        body: str = "",
        attachments: Optional[Union[List[str], str]] = None,
        html: bool = False,
        images: Optional[Union[List[str], str]] = None,
        cc: Optional[Union[List[str], str]] = None,
        bcc: Optional[Union[List[str], str]] = None,
        attachment_position: Optional[AttachmentPosition] = AttachmentPosition.TOP,
    ) -> bool:
        """Send SMTP email

        :param sender: who is sending, ie. 'from'
        :param recipients: who is receiving, ie. 'to'
        :param subject: mail subject field
        :param body: mail body content
        :param attachments: list of filepaths to attach
        :param html: if message content is in HTML, default `False`
        :param images: list of filepaths for inline images
        :param cc: list of email addresses for email 'cc' field
        :param bcc: list of email addresses for email 'bcc' field
        :param attachment_position: content position for attachment, default `top`

        Valid sender values:

        - First Lastname <address@domain>
        - address@domain

        Example:

        .. code-block:: robotframework

            Send Message  sender@domain.com  recipient@domain.com
            ...           cc=need_to_know@domain.com
            ...           bcc=hidden_copy@domain.com
            ...           subject=Greetings Software Robot Developer
            ...           body=${email_body}
            ...           attachments=${CURDIR}${/}report.pdf

            # Fixing attachments to the bottom of the content
            Send Message  sender@domain.com  recipient@domain.com
            ...           subject=Greetings Software Robot Developer
            ...           body=${email_body}
            ...           attachments=${CURDIR}${/}report.pdf
            ...           attachment_position=bottom
        """
        evaluated_attachment_position = to_attachment_position(attachment_position)
        add_charset(self.encoding, QP, QP, self.encoding)
        to, attachments, images = self._handle_message_parameters(
            recipients, attachments, images
        )
        msg = MIMEMultipart()

        if evaluated_attachment_position == AttachmentPosition.TOP:
            self._add_attachments_to_msg(attachments, msg)

        sender = sender.encode("idna").decode("ascii")
        msg_to = ",".join(to).encode("idna").decode("ascii")
        msg["From"] = sender
        msg["To"] = msg_to
        msg["Subject"] = Header(subject, self.encoding)
        recipients = to if isinstance(to, list) else [to]
        if cc:
            msg["Cc"] = ",".join(cc) if isinstance(cc, list) else cc
            recipients += cc if isinstance(cc, list) else cc.split(",")
        if bcc:
            recipients += bcc if isinstance(bcc, list) else bcc.split(",")

        self._add_message_content(html, images, body, msg)

        if evaluated_attachment_position == AttachmentPosition.BOTTOM:
            self._add_attachments_to_msg(attachments, msg)

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

    def _add_message_content(self, html, images, body, msg):
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

    def get_decoded_email_body(
        self, message, html_first: bool = False
    ) -> Tuple[str, bool]:
        """Decodes email body and extracts its text/html content.

        Automatically detects character set if the header is not set.

        :param message: Raw 7-bit message body input e.g. from `imaplib`. Double
            encoded in quoted-printable and latin-1
        :param html_first: Prioritize html extraction over text when this is True
        :returns: Message body as unicode string and a boolean telling if the message
            has attachments
        """
        if not message.is_multipart():
            content_charset = message.get_content_charset()
            text = str(
                message.get_payload(decode=True),
                content_charset or self.encoding,
                "ignore",
            )
            return text.strip(), False

        text = html = None
        has_attachments = False

        for part in message.walk():
            if not part:
                continue
            content_filename = get_part_filename(part)
            if content_filename:
                has_attachments = True
                continue
            content_type = "text/plain"
            _data = ""
            content_charset = part.get_content_charset()
            if content_charset:
                content_type = part.get_content_type()
            payload = part.get_payload(decode=True)
            if payload:
                _data = str(payload, str(content_charset), "ignore")

            if content_type == "text/plain":
                text = _data
            elif content_type == "text/html":
                html = _data

        if html_first:
            data = html or text
        else:
            data = text or html
        data = data.strip() if data else ""
        return data, has_attachments

    @imap_connection
    def _do_actions_on_messages(
        self,
        criterion: Union[str, dict],
        actions: list,
        labels: str = None,
        source_folder: str = None,
        target_folder: str = None,
        limit: int = None,
        overwrite: bool = False,
        readonly: bool = False,
        prefix: str = "",
    ) -> list:
        selected_folder = source_folder or self.selected_folder
        folders = self.get_folder_list(subdirectory=selected_folder)
        result = {"actions_done": 0, "message_count": 0, "ids": [], "uids": {}}

        if source_folder:
            for folder in folders:
                if "Noselect" in folder["flags"]:
                    continue
                folder_name = folder["name"]
                self.select_folder(folder_name, readonly)
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
                    prefix=prefix,
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
                    mail_uid, message = self._fetch_uid_and_message(mail_id, actions)
                    if mail_uid is None or mail_uid in result["uids"].keys():
                        continue
                    message["uid"] = mail_uid
                    result["uids"][mail_uid] = message
            return True
        else:
            self.logger.warning("Search result not OK: %s", status)
            return False

    def _get_mail_uids_and_dicts(self, mail):
        mail_uids = []
        mail_dicts = []
        if isinstance(mail, list):
            mail_uids = [m["uid"] for m in mail]
            mail_dict = None
            mail_dicts = mail
        else:
            try:
                mail_uid, mail_dict = mail
                mail_uids = [mail_uid]
                mail_dicts = [mail_dict]
            except ValueError:
                mail_uid = mail["uid"]
                mail_dict = mail
                mail_uids = [mail_uid]
                mail_dicts = [mail]
        return mail_uids, mail_dicts

    def _command_mail_uid(self, command, uid, m_op="", m_param="", target_folder=None):
        if target_folder:
            action_status, _ = self.imap_conn.uid(command, uid, target_folder)
            self.logger.debug(
                "%s %s %s RESULT %s", command, uid, target_folder, action_status
            )
        else:
            action_status, _ = self.imap_conn.uid(command, uid, m_op, m_param)
            self.logger.info(
                "%s %s %s %s RESULT %s",
                command,
                uid,
                m_op,
                m_param,
                action_status,
            )
        return action_status

    def _perform_actions(  # noqa: C901 pylint: disable=too-many-branches
        self,
        actions: list,
        mail: Union[dict, list],
        labels: str = None,
        target_folder: str = None,
        overwrite: bool = False,
        prefix: str = "",
    ):
        action_status = True
        mail_uids, mail_dicts = self._get_mail_uids_and_dicts(mail)
        store_params = {
            Action.glabel_add: ["+X-GM-LABELS", f"({labels})"],
            Action.glabel_remove: ["-X-GM-LABELS", f"({labels})"],
            Action.msg_delete: ["+FLAGS", FLAG_DELETED],
            Action.msg_flag: ["+FLAGS", FLAG_FLAGGED],
            Action.msg_unflag: ["-FLAGS", FLAG_FLAGGED],
            Action.msg_read: ["+FLAGS", FLAG_SEEN],
            Action.msg_unread: ["-FLAGS", FLAG_SEEN],
            Action.msg_trash: ["+FLAGS", FLAG_TRASH],
        }
        for act in actions:
            action = to_action(act)
            if action == Action.msg_list:
                continue
            if action in store_params.keys():
                m_op, m_param = store_params[action]
                for uid in mail_uids:
                    action_status = self._command_mail_uid("STORE", uid, m_op, m_param)
            elif action == Action.msg_copy:
                for uid in mail_uids:
                    action_status = self._command_mail_uid(
                        "COPY", uid, target_folder=target_folder
                    )
            elif action == Action.msg_move:
                m_op, m_param = store_params[Action.msg_delete]
                for uid in mail_uids:
                    if " " in target_folder:
                        target_folder = f'"{target_folder}"'
                    action_status = self._command_mail_uid(
                        "COPY", uid, target_folder=target_folder
                    )
                    action_status = self._command_mail_uid("STORE", uid, m_op, m_param)
            elif action == Action.msg_save and len(mail_dicts) > 0:
                if target_folder is None:
                    target_folder = os.path.expanduser("~")
                for mail_dict in mail_dicts:
                    action_status = self._save_eml_file(
                        mail_dict, target_folder, overwrite, prefix
                    )
            elif action == Action.msg_attachment_save and len(mail_dicts) > 0:
                if target_folder is None:
                    target_folder = os.path.expanduser("~")
                for mail_dict in mail_dicts:
                    self._save_attachment(mail_dict, target_folder, overwrite, prefix)
            else:
                # TODO: mypy should handle enum exhaustivity validation
                raise ValueError(
                    f"Unsupported email action or insufficient input data: {action}"
                )
        return action_status

    @imap_connection
    def delete_message(
        self,
        criterion: Union[str, dict] = None,
        source_folder: str = None,
    ) -> bool:
        """Delete single message from server based on criterion.

        :param criterion: filter messages based on this search, can also be a
         message dictionary
        :param source_folder: defaults to already selected folder, but can be
         set to delete message in a specific folder
        :return: True if success, False if not

        If criterion does not return exactly 1 message then delete is not done.

        Example:

        .. code-block:: robotframework

            Delete Message  SUBJECT \"Greetings RPA developer\"
        """
        selected_folder = source_folder or self.selected_folder
        if isinstance(criterion, dict):
            readonly = False
            self.select_folder(selected_folder, readonly)
            status = self._perform_actions(
                [Action.msg_delete],
                criterion,
            )
            result = {
                "actions_done": 1 if status else 0,
                "message_count": 1,
                "ids": [criterion["uid"]],
                "uids": {criterion["uid"]: criterion},
            }
            self.imap_conn.expunge()
        else:
            result = self._do_actions_on_messages(
                criterion,
                actions=[Action.msg_delete],
                limit=1,
                source_folder=selected_folder,
            )
            self.imap_conn.expunge()
        return result["actions_done"] == 1

    @imap_connection
    def delete_messages(
        self,
        criterion: Union[str, list] = None,
        limit: int = None,
        source_folder: str = None,
    ) -> bool:
        """Delete messages from server based on criterion.

        :param criterion: filter messages based on this search, can also be a
         list of message dictionaries
        :param limit: maximum number of message to delete
        :param source_folder: defaults to already selected folder, but can be
         set to delete message in a specific folder
        :return: True if success, False if not

        Example:

        .. code-block:: robotframework

            Delete Messages  SUBJECT Greetings
        """
        selected_folder = source_folder or self.selected_folder
        if isinstance(criterion, list):
            readonly = False
            self.select_folder(selected_folder, readonly)
            status = self._perform_actions(
                [Action.msg_delete],
                criterion,
            )
            self.imap_conn.expunge()
            return status
        else:
            result = self._do_actions_on_messages(
                criterion,
                actions=[Action.msg_delete],
                limit=limit,
                source_folder=selected_folder,
            )
        return (
            result["actions_done"] > 0
            and result["actions_done"] == result["message_count"]
        )

    @imap_connection
    def save_messages(
        self,
        criterion: Optional[Union[str, dict, list]] = None,
        target_folder: Optional[str] = None,
        prefix: Optional[str] = None,
    ) -> bool:
        # pylint: disable=C0301
        """Save messages based on criteria and store them to target folder
        with attachment files.

        Does not save message if `target_folder` is not given.

        :param criterion: filter messages based on this, defaults to ""
        :param target_folder: path to folder where message are saved, defaults to None
        :param prefix: optional filename prefix added to the attachments, empty by
            default
        :return: True if succeeded, False otherwise

        Example:

        .. code-block:: robotframework

            Save Messages  SUBJECT Important message  target_folder=${USERDIR}${/}messages
        """  # noqa: E501
        prefix = prefix or ""
        if target_folder is None:
            target_folder = os.path.expanduser("~")
        if isinstance(criterion, (dict, list)):
            status = self._perform_actions(
                [Action.msg_save], criterion, target_folder=target_folder, prefix=prefix
            )
            return status
        else:
            result = self._do_actions_on_messages(
                criterion,
                actions=[Action.msg_save],
                target_folder=target_folder,
                prefix=prefix,
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
        self,
        criterion: str = "",
        target_folder: Optional[str] = None,
        overwrite: bool = False,
        prefix: Optional[str] = None,
    ) -> List[str]:
        # pylint: disable=C0301
        """Save mail attachments of emails matching criterion on the local disk.

        :param criterion: attachments are saved for mails matching this, defaults to ""
        :param target_folder: local folder for saving attachments to (needs to exist),
            defaults to user's home directory if None
        :param overwrite: overwrite existing file if True, defaults to False
        :param prefix: optional filename prefix added to the attachments, empty by
            default
        :return: list of saved attachments (absolute file paths) of all emails

        Example:

        .. code-block:: robotframework

            ${attachments} =    Save Attachments    SUBJECT "rpa task"
            ...    target_folder=${CURDIR}${/}messages  overwrite=${True}
            FOR  ${file}  IN  @{attachments}
                OperatingSystem.File Should Exist  ${file}
            END
        """  # noqa: E501
        attachments_saved = []
        prefix = prefix or ""
        messages = self.list_messages(criterion)
        for msg in messages:
            attachments_saved.extend(
                self.save_attachment(msg, target_folder, overwrite, prefix)
            )
        return attachments_saved

    def save_attachment(
        self,
        message: Union[dict, Message],
        target_folder: Optional[str],
        overwrite: bool,
        prefix: Optional[str] = None,
    ) -> List[str]:
        # pylint: disable=C0301
        """Save mail attachment of a single given email on the local disk.

        :param message: message item
        :param target_folder: local folder for saving attachments to (needs to exist),
            defaults to user's home directory if None
        :param overwrite: overwrite existing file if True, defaults to False
        :param prefix: optional filename prefix added to the attachments, empty by
            default
        :return: list of saved attachments (list of absolute filepaths) in one email

        Example:

        .. code-block:: robotframework

            @{emails} =    List Messages    ALL
            FOR    ${email}    IN    @{emails}
                IF    ${email}[Has-Attachments]
                    Log To Console    Saving attachment for: ${email}[Subject]
                    ${attachments} =    Save Attachment
                    ...    ${email}
                    ...    target_folder=${CURDIR}
                    ...    overwrite=${True}
                    Log To Console    Saved attachments: ${attachments}
                END
            END
        """  # noqa: E501
        prefix = prefix or ""
        if target_folder is None:
            target_folder = os.path.expanduser("~")
        return self._save_attachment(message, target_folder, overwrite, prefix)

    def _save_attachment(self, message, target_folder, overwrite, prefix) -> List[str]:
        attachments_saved = []
        msg = message["Message"] if isinstance(message, dict) else message

        for part in msg.walk():
            content_maintype = part.get_content_maintype()
            filename = None
            if content_maintype != "multipart":
                filename = get_part_filename(part)
            if not filename:
                continue

            filepath = Path(target_folder) / Path(f"{prefix}{filename}").name
            if not overwrite:
                filepath = counter_duplicate_path(filepath)
            self.logger.info("Attachment filepath: %r", filepath)
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
                self.logger.info(
                    "Attachment %r did not have payload to write",
                    filename,
                )
        return attachments_saved

    def _save_eml_file(self, message, target_folder, overwrite, prefix):
        save_status = True
        emlfile = f"{prefix}{message['uid']}.eml"
        full_emlfile_path = Path(os.path.join(target_folder, emlfile))
        if not full_emlfile_path.exists() or overwrite:
            with open(full_emlfile_path, "wb") as f:
                if "bytes" in message.keys():
                    f.write(message["bytes"])
                elif "Message" in message:
                    f.write(message["Message"].as_bytes())
                else:
                    save_status = False
                    self.logger.error(
                        "Save failed. Unable to get message byte content."
                    )
        elif full_emlfile_path.exists() and not overwrite:
            self.logger.warning("Did not overwrite file: %s", full_emlfile_path)
        return save_status

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
            kwparams["directory"] = f'"{subdirectory}"'
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
    def flag_messages(
        self, criterion: Union[str, dict] = None, unflag: bool = False
    ) -> Any:
        """Mark messages as `flagged`

        :param criterion: mark messages matching criterion
        :param unflag: to mark messages as not `flagged`
        :return: successful operations (int), matching messages (int)

        Example:

        .. code-block:: robotframework

            ${flagged}  ${oftotal}    Flag Messages   SUBJECT rpa
            ${unflagged}  ${oftotal}  Flag Messages   SUBJECT rpa  unflag=True
        """
        action = Action.msg_unflag if unflag else Action.msg_flag
        if isinstance(criterion, dict):
            status = self._perform_actions(mail=criterion, actions=[action])
            return status
        else:
            result = self._do_actions_on_messages(criterion, actions=[action])
            return (
                result["actions_done"] > 0
                and result["actions_done"] == result["message_count"]
            )

    @imap_connection
    def unflag_messages(self, criterion: Union[str, dict] = None) -> Any:
        """Mark messages as not `flagged`

        :param criterion: mark messages matching criterion
        :return: successful operations (int), matching messages (int)

        Example:

        .. code-block:: robotframework

            ${unflagged}  ${oftotal}  Unflag Messages   SUBJECT rpa
        """
        return self.flag_messages(criterion, unflag=True)

    @imap_connection
    def mark_as_read(
        self, criterion: Union[str, dict] = None, unread: bool = False
    ) -> Any:
        """Mark messages as `read`

        :param criterion: mark messages matching criterion
        :param unread: to mark messages as not `read`
        :return: successful operations (int), matching messages (int)

        Example:

        .. code-block:: robotframework

            ${read}  ${oftotal}  Mark As Read   SUBJECT rpa
        """
        action = Action.msg_unread if unread else Action.msg_read
        if isinstance(criterion, dict):
            status = self._perform_actions(mail=criterion, actions=[action])
            return status
        else:
            result = self._do_actions_on_messages(criterion, actions=[action])
            return (
                result["actions_done"] > 0
                and result["actions_done"] == result["message_count"]
            )

    @imap_connection
    def mark_as_unread(self, criterion: Union[str, dict] = None) -> Any:
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

    def _fetch_uid_and_message(self, mail_id, actions):
        message_dict = None
        _, data = self.imap_conn.fetch(mail_id, "(UID RFC822)")
        pattern_uid = re.compile(r".*UID (\d+) RFC822")
        decoded_data = bytes.decode(data[0][0]) if data[0] else None
        self.logger.debug("message identification: %s", decoded_data)
        match_result = pattern_uid.match(decoded_data) if decoded_data else None
        uid = match_result.group(1) if match_result else None
        if uid:
            message_dict = self._fetch_message_dict(mail_id, data, actions)

        key_to_change = None
        message_id_to_add = None
        if message_dict:
            for key, val in message_dict.items():
                if key.lower() == "message-id":
                    key_to_change = key
                    message_id_to_add = (
                        str(val).replace("<", "").replace(">", "").strip()
                    )
            if key_to_change:
                message_dict["Message-ID"] = message_id_to_add
                if key_to_change != "Message-ID":
                    del message_dict[key_to_change]
        return uid, message_dict

    def _fetch_message_dict(self, mail_id, data, actions):
        # _, data = self.imap_conn.fetch(mail_id, "(RFC822)")
        message = message_from_bytes(data[0][1])
        message_dict = {"Mail-Id": mail_id, "Message": message, "Body": ""}
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
        criterion: Union[str, dict] = None,
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
        selected_folder = source_folder or self.selected_folder
        if target_folder is None or len(target_folder) == 0:
            raise KeyError("Can't move messages without target_folder")
        if isinstance(criterion, dict):
            readonly = False
            self.select_folder(selected_folder, readonly)
            status = self._perform_actions(
                mail=criterion,
                actions=[Action.msg_move],
                target_folder=target_folder,
            )
            result = {
                "actions_done": 1 if status else 0,
                "message_count": 1,
                "ids": [criterion["uid"]],
                "uids": {criterion["uid"]: criterion},
            }
        else:
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
        criterion: Union[str, dict],
        action: bool = True,
        source_folder: str = None,
    ) -> bool:
        if isinstance(criterion, dict):
            selected_folder = source_folder or self.selected_folder
            self.select_folder(selected_folder)
            status = self._perform_actions(
                mail=criterion,
                actions=[action],
                labels=labels,
            )
            return status
        else:
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
        prefix: str = None,
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
        :param prefix: prefix to be added into filename (for example: msg_save)
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
            prefix=prefix,
        )
        return (
            result["actions_done"] > 0
            and result["actions_done"] == result["message_count"]
        )

    @staticmethod
    def _ensure_path_object(source: FilePath) -> Path:
        if not isinstance(source, Path):
            source = Path(source)
        return source.expanduser().resolve()

    def email_to_document(
        self, input_source: Union[FilePath, BinaryIO, bytes], output_path: FilePath
    ):
        """Convert a raw e-mail into a Word document.

        This keyword extracts the HTML (or Text) content from the passed input e-mail
        and saves it into docx format at the provided output path.

        :param input_source: Path, bytes or file-like object with the input raw e-mail
            content
        :param output_path: Where to save the output docx file

        Example:

        **Robot Framework**

        .. code-block:: robotframework

            Convert email to docx
                ${mail_file} =     Get Work Item File    mail.eml
                Email To Document    ${mail_file}    ${OUTPUT_DIR}${/}mail.docx

        **Python**

        .. code-block:: python

            from pathlib import Path
            from RPA.Email.ImapSmtp import ImapSmtp
            from RPA.Robocorp.WorkItems import WorkItems

            lib_work = WorkItems()
            lib_mail = ImapSmtp()

            def convert_email_to_docx():
                lib_work.get_input_work_item()
                mail_file = lib_work.get_work_item_file("mail.eml")
                lib_mail.email_to_document(mail_file, Path("./output") / "mail.docx")

            convert_email_to_docx()
        """

        if hasattr(input_source, "read"):
            self.logger.info("Reading raw e-mail bytes from the provided source object")
            data = input_source.read()
        elif isinstance(input_source, bytes):
            self.logger.info("Using the provided source bytes as raw e-mail content")
            data = input_source
        else:
            input_source = self._ensure_path_object(input_source)
            self.logger.info("Reading raw e-mail bytes from: %s", input_source)
            data = input_source.read_bytes()
        assert isinstance(
            data, bytes
        ), "bytes expected for e-mail parsing, got %s" % type(data)

        self.logger.info("Getting the html/text from the raw e-mail")
        message = message_from_bytes(data)
        body, _ = self.get_decoded_email_body(message, html_first=True)

        h2d_parser = HtmlToDocx()
        self.logger.debug("Converting html/text content:\n%s", body)
        docx = h2d_parser.parse_html_string(body)
        output_path = self._ensure_path_object(output_path)
        self.logger.info("Writing converted document into: %s", output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        docx.save(output_path)

    def generate_oauth_string(self, username: str, access_token: str) -> str:
        """Generate and return an OAuth2 string compatible with the IMAP/POP/SMTP
        XOAUTH2 protocol.

        This string usually gets passed to the ``Authorize`` keyword as `password` when
        `is_oauth=${True}`.

        :param username: The e-mail address you're going to send the e-mail with.
        :param access_token: Access token string found in the dictionary obtained with
             ``Get OAuth Token`` or ``Refresh OAuth Token``.
        :returns: Base64 encoded string packing these credentials and replacing the
            legacy `password` when enabling the OAuth2 flow.

        **Example: Robot Framework**

        .. code-block:: robotframework

            *** Tasks ***
            Authorize ImapSmtp
                ${password} =   Generate OAuth String    ${username}
                ...    ${token}[access_token]
                Authorize    account=${username}    is_oauth=${True}
                ...     password=${password}
        """
        auth_string = f"user={username}\1auth=Bearer {access_token}\1\1"
        return base64.b64encode(auth_string.encode()).decode()
