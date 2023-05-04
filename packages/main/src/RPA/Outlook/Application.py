import atexit
import logging
import platform
import struct
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, List, Union, Optional

from RPA.Email.common import counter_duplicate_path

if platform.system() == "Windows":
    import win32api
    import win32com.client
    import pywintypes
else:
    logging.getLogger(__name__).warning(
        "RPA.Outlook.Application library works only on Windows platform"
    )


def _to_unsigned(val):
    return struct.unpack("L", struct.pack("l", val))[0]


@contextmanager
def catch_com_error():
    """Try to convert COM errors to human readable format."""
    try:
        yield
    except pywintypes.com_error as err:  # pylint: disable=no-member
        if err.excepinfo:
            try:
                msg = win32api.FormatMessage(_to_unsigned(err.excepinfo[5]))
            except Exception:  # pylint: disable=broad-except
                msg = err.excepinfo[2]
        else:
            try:
                msg = win32api.FormatMessage(_to_unsigned(err.hresult))
            except Exception:  # pylint: disable=broad-except
                msg = err.strerror
        raise RuntimeError(msg) from err


class Application:
    # pylint: disable=C0301
    """`Outlook.Application` is a library for controlling the Outlook application.

    *Note*. Library works only Windows platform.

    Library will automatically close the Outlook application at the end of the
    task execution. This can be changed by importing library with `autoexit` setting.

    .. code-block:: robotframework

        *** Settings ***
        Library                 RPA.Outlook.Application   autoexit=${FALSE}

    **About Email Filtering**

    Emails can be filtered according to specification set by Restrict method of the Item
    class https://docs.microsoft.com/en-us/office/vba/api/outlook.items.restrict.

    Couple of examples:

    .. code-block:: robotframework

        Get Emails
        ...   email_filter=[Subject]='test email'

        Move Emails
        ...   email_filter=[SenderEmailAddress]='hello@gmail.com'

    **Examples**

    **Robot Framework**

    .. code-block:: robotframework

        *** Settings ***
        Library                 RPA.Outlook.Application
        Task Setup              Open Application
        Suite Teardown          Quit Application

        *** Variables ***
        ${RECIPIENT}            address@domain.com

        *** Tasks ***
        Send message
            Send Message       recipients=${RECIPIENT}
            ...                subject=This is the subject
            ...                body=This is the message body
            ..                 attachments=approved.png

    **Python**

    .. code-block:: python

        from RPA.Outlook.Application import Application

        def send_message():
            app = Application()
            app.open_application()
            app.send_message(
                recipients='EMAILADDRESS_1, EMAILADDRESS_2',
                subject='email subject',
                body='email body message',
                attachments='../orders.csv'

    For more information, see: https://docs.microsoft.com/en-us/previous-versions/office/developer/office-2007/bb219950(v=office.12)
    """  # noqa: E501

    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    ROBOT_LIBRARY_DOC_FORMAT = "REST"

    def __init__(self, autoexit: bool = True) -> None:
        self.logger = logging.getLogger(__name__)
        self.app = None

        if platform.system() != "Windows":
            self.logger.warning(
                "Outlook application library requires Windows dependencies to work."
            )
        if autoexit:
            atexit.register(self.quit_application)

    def open_application(
        self, visible: bool = False, display_alerts: bool = False
    ) -> None:
        """Open the Outlook application.

        :param visible: show window after opening, default False
        :param display_alerts: show alert popups, default False
        """
        with catch_com_error():
            self.app = win32com.client.gencache.EnsureDispatch("Outlook.Application")

            if hasattr(self.app, "Visible"):
                self.app.Visible = visible

            # show eg. file overwrite warning or not
            if hasattr(self.app, "DisplayAlerts"):
                self.app.DisplayAlerts = display_alerts

    def close_document(self, save_changes: bool = False) -> None:
        """Close the active document (if open).

        :param save_changes: if changes should be saved on close, default False
        """
        if not self.app:
            return
        if hasattr(self.app, "ActiveDocument"):
            self.app.ActiveDocument.Close(save_changes)

    def quit_application(self, save_changes: bool = False) -> None:
        """Quit the application.

        :param save_changes: if changes should be saved on quit, default False
        """
        if not self.app:
            return
        self.close_document(save_changes)
        self.app.Quit()
        self.app = None

    def send_message(
        self,
        recipients: Union[str, List[str]],
        subject: str,
        body: str,
        html_body: bool = False,
        attachments: Optional[Union[str, List[str]]] = None,
        save_as_draft: bool = False,
        cc_recipients: Optional[Union[str, List[str]]] = None,
        bcc_recipients: Optional[Union[str, List[str]]] = None,
    ) -> bool:
        """Send message with Outlook

        :param recipients: list of addresses
        :param subject: email subject
        :param body: email body
        :param html_body: True if body contains HTML, defaults to False
        :param attachments: list of filepaths to include in the email, defaults to []
        :param save_as_draft: message is saved as draft when `True`
         instead (and not sent)
        :return: `True` if there were no errors
        """
        self.logger.warning(
            "Keyword 'Send Message' is deprecated, "
            "and will be removed in a future version."
            "Use 'Send Email' instead."
        )
        return self.send_email(
            recipients,
            subject,
            body,
            html_body,
            attachments,
            save_as_draft,
            cc_recipients,
            bcc_recipients,
        )

    def send_email(
        self,
        recipients: Union[str, List[str]],
        subject: str,
        body: str,
        html_body: bool = False,
        attachments: Optional[Union[str, List[str]]] = None,
        save_as_draft: bool = False,
        cc_recipients: Optional[Union[str, List[str]]] = None,
        bcc_recipients: Optional[Union[str, List[str]]] = None,
    ) -> bool:
        """Send email with Outlook

        :param recipients: list of addresses
        :param subject: email subject
        :param body: email body
        :param html_body: True if body contains HTML, defaults to False
        :param attachments: list of filepaths to include in the email, defaults to []
        :param save_as_draft: email is saved as draft when `True`
        :param cc_recipients: list of addresses for CC field, default None
        :param bcc_recipients: list of addresses for BCC field, default None
        :return: `True` if there were no errors

        Example:

        .. code-block:: python

            library = Outlook()
            library.open_application()
            cc_recipients = ["recipient3@domain.com","recipient4@domain.com"]
            library.send_email(
                recipients="recipient1@domain.com",
                cc_recipients=cc_recipients,
                bcc_recipients="recipient3@domain.com;recipient4@domain.com",
                subject="hello from Outlook",
                body="empty body",
                attachments=os.path.join(os.path.curdir, "example.xslx")
            )

        .. code-block:: robotframework

            ${cc}=  Create List   recipient3@domain.com   recipient4@domain.com
            Send Email
            ...    recipients=recipient1@domain.com
            ...    cc_repients=${cc}
            ...    bcc_repients=recipient5@domain.com;recipient6@domain.com
            ...    subject=hello from Outlook
            ...    body=empty body
            ...    attachments=${CURDIR}${/}example.xlsx
        """
        # pylint: disable=no-member
        attachments = attachments or []
        if not isinstance(attachments, list):
            attachments = str(attachments).split(";")

        try:
            mail = self.app.CreateItem(0)
            mail.Subject = subject
            self._add_all_recipients(mail, recipients, cc_recipients, bcc_recipients)

            if html_body:
                mail.HTMLBody = body
            else:
                mail.Body = body

            self._add_attachments(mail, attachments)

            if save_as_draft:
                mail.Save()
                self.logger.debug("Email draft saved")
            else:
                mail.Send()
                self.logger.debug("Email sent")
        except pywintypes.com_error as e:
            self.logger.error(
                f"Mail {'saving' if save_as_draft else 'sending'} failed: %s", e
            )
            return False
        return True

    def _add_all_recipients(self, email, recipients, cc_recipients, bcc_recipients):
        if isinstance(recipients, list):
            email.To = ";".join(recipients)
        else:
            email.To = recipients
        if cc_recipients:
            if isinstance(cc_recipients, list):
                email.CC = ";".join(cc_recipients)
            else:
                email.CC = cc_recipients
        if bcc_recipients:
            if isinstance(bcc_recipients, list):
                email.BCC = ";".join(bcc_recipients)
            else:
                email.BCC = bcc_recipients

    def _add_attachments(self, email, attachments):
        for attachment in attachments:
            filepath = Path(attachment).absolute()
            email.Attachments.Add(str(filepath))

    def _is_email_too_old(self, email):
        now = datetime.now().timestamp()
        msg_time = email["ReceivedTimestamp"]
        timediff = now - msg_time
        return timediff > 30.0

    def _check_for_matching(self, criterion, email):
        crit_key, crit_val = criterion.split(":", 1)
        crit_key = crit_key.upper()
        crit_val = crit_val.lower()
        match_found = None

        if crit_key.upper() == "SUBJECT" and crit_val in email["Subject"].lower():
            match_found = email
        elif crit_key.upper() == "SENDER" and crit_val in email["Sender"].lower():
            match_found = email
        elif crit_key.upper() == "BODY" and crit_val in email["Body"].lower():
            match_found = email

        return match_found

    def wait_for_message(
        self, criterion: str = None, timeout: float = 5.0, interval: float = 1.0
    ) -> Any:
        """Wait for email matching `criterion` to arrive into mailbox.

        :param criterion: message filter to wait for, defaults to ""
        :param timeout: total time in seconds to wait for email, defaults to 5.0
        :param interval: time in seconds for new check, defaults to 1.0
        :return: list of messages or False

        Possible wait criterias are: SUBJECT, SENDER and BODY

        Example:

        .. code-block:: robotframework

            Wait for message     SUBJECT:rpa task calling    timeout=300    interval=10
        """
        self.logger.warning(
            "Keyword 'Wait For Message' is deprecated, "
            "and will be removed in a future version."
            "Use 'Wait For Email' instead."
        )
        return self.wait_for_email(criterion, timeout, interval)

    def wait_for_email(
        self, criterion: str = None, timeout: float = 5.0, interval: float = 1.0
    ) -> Any:
        """Wait for email matching `criterion` to arrive into mailbox.

        :param criterion: email filter to wait for, defaults to ""
        :param timeout: total time in seconds to wait for email, defaults to 5.0
        :param interval: time in seconds for new check, defaults to 1.0
        :return: list of messages or False

        Possible wait criterias are: SUBJECT, SENDER and BODY

        Example:

        .. code-block:: robotframework

            Wait for Email     SUBJECT:rpa task calling    timeout=300    interval=10
        """
        if self.app is None:
            raise ValueError("Requires active Outlook Application")
        if criterion is None:
            self.logger.warning(
                "Wait for message requires criteria for which message to wait for."
            )
            return False
        end_time = time.time() + float(timeout)
        namespace = self.app.GetNamespace("MAPI")
        inbox = namespace.GetDefaultFolder(6)
        while time.time() < end_time:
            messages = inbox.Items
            messages.Sort("[ReceivedTime]", True)
            for msg in messages:
                if type(msg).__name__ != "_MailItem":
                    continue
                m = self._mail_item_to_dict(msg)
                if self._is_email_too_old(m):
                    break
                else:
                    match_found = self._check_for_matching(criterion, m)
                    if match_found:
                        return match_found
            time.sleep(interval)
        raise AssertionError("Did not find matching message in the Outlook inbox")

    def get_emails(
        self,
        account_name: str = None,
        folder_name: str = None,
        email_filter: str = None,
        save_attachments: bool = False,
        attachment_folder: str = None,
        sort: bool = False,
        sort_key: str = None,
        sort_descending: bool = True,
    ) -> List:
        """Get emails from a specified email folder. Can be used to save attachments.

        :param account_name: needs to be given if there are shared accounts in use,
         defaults to None
        :param folder_name: target folder where to get emails from, default Inbox
        :param email_filter: how to filter email, default no filter,
         ie. all emails in folder
        :param save_attachments: if attachments should be saved, defaults to False
        :param attachment_folder: target folder where attachments are saved,
         defaults to current directory
        :param sort: if emails should be sorted, defaults to False
        :param sort_key: needs to be given if emails are to be sorted
        :param sort_descending: set to False for ascending sort, defaults to True
        :return: list of emails (list of dictionaries)

        Example:

        .. code-block:: robotframework

            ${emails}=  Get Emails
            ...    email_folder=priority
            ...    email_filter=[Subject]='incoming order'
            ...    save_attachments=True
            ...    attachment_folder=%{ROBOT_ROOT}${/}attachments
            ...    sort=True
            ...    sort_key=Received
            ...    sort_descending=False
        """
        folder = self._get_folder(account_name, folder_name)
        folder_messages = folder.Items if folder else []
        messages = []
        if folder_messages and email_filter:
            try:
                folder_messages = folder_messages.Restrict(email_filter)
            except Exception:
                raise AttributeError(  # pylint: disable=raise-missing-from
                    "Invalid email filter '%s'" % email_filter
                )
        if folder_messages and sort:
            sort_key = sort_key or "ReceivedTime"
            try:
                folder_messages.Sort(f"[{sort_key}]", sort_descending)
            except Exception:
                raise AttributeError(  # pylint: disable=raise-missing-from
                    "Invalid email sort key '%s'" % sort_key
                )
        for message in folder_messages:
            if type(message).__name__ != "_MailItem":
                continue
            if save_attachments:
                self.save_email_attachments(message.Attachments, attachment_folder)
            messages.append(self._mail_item_to_dict(message))
        return messages

    def _get_folder(self, account_name, email_folder):
        namespace = self.app.GetNamespace("MAPI")
        if not account_name and not email_folder:
            self.logger.warning("Getting items from default account inbox")
            return namespace.GetDefaultFolder(6)
        email_folder = email_folder or "Inbox"
        folder = None
        if account_name:
            account_folder = self._get_account_folder(namespace, account_name)
            if account_folder:
                folder = self._get_matching_folder(email_folder, account_folder)
            else:
                raise AttributeError("Did not find account by name '%s'" % account_name)
        else:
            folder = self._get_matching_folder(email_folder, None)
        return folder if folder else []

    def _get_account_folder(self, namespace, account_name):
        account_folder = None
        for f in namespace.Folders:
            if f.Name == account_name:
                account_folder = f
                break
        return account_folder

    def _get_matching_folder(self, folder_name, folder=None):
        folders = []
        if not folder or isinstance(folder, str):
            folders = self.app.GetNamespace("MAPI").Folders
        elif isinstance(folder, list):
            folders = folder
        else:
            folders = folder.Folders
        for f in folders:
            if folder_name == f.Name:
                self.logger.debug("Found matching folder: %s", f.Name)
                return f
            emails = self._get_matching_folder(folder_name, f)
            if emails:
                return emails
        return None

    def save_email_attachments(
        self, attachments: Any, attachment_folder: str, overwrite: bool = False
    ) -> None:
        """Save email attachments.

        Note. Keyword "Get Emails" can be also used to save attachments.

        :param attachments: all attachments from email or single attachment
        :param attachment_folder: target folder where attachments are saved,
            defaults to current directory
        :param overwrite: overwrite existing file if True, defaults to False

        Example:

        .. code-block:: robotframework

            ${emails} =  Get Emails
            ...    email_folder=priority
            FOR  ${email}  IN   @{emails}
                FOR  ${attachment}  IN  @{email}[Attachments]
                    IF  ${attachment}[size] < 100000   # bytes
                        Save Email Attachments
                        ...  ${attachment}
                        ...  ${CURDIR}${/}attachments
                    ELSE IF  ".pdf" in "${attachment}[filename]"
                        Save Email Attachments
                        ...  ${attachment}
                        ...  ${CURDIR}${/}attachments${/}pdf
                    END
                END
            END
        """
        attachment_target = Path(attachment_folder) if attachment_folder else Path(".")
        if isinstance(attachments, dict):
            email_attachments = [attachments["item"]]
        else:
            email_attachments = attachments
        for attachment in email_attachments:
            file_path = (attachment_target / attachment.FileName).absolute()
            if not overwrite:
                file_path = counter_duplicate_path(file_path)
            attachment.SaveAsFile(file_path)

    def mark_email_as_read(self, email: Any, read: bool = True) -> None:
        """Mark email 'read' property. Can be used to mark email as unread.

        :param email: target email
        :param read: True marks email as Read, False as Unread

        Example:

        .. code-block:: robotframework

            ${emails}=  Get Emails
            # Mark all as read
            FOR  ${email}  IN  @{emails}
                Mark Email As Read  ${email}
            END

            # Mark all as unread
            FOR  ${email}  IN  @{emails}
                Mark Email As Read  ${email}  False
            END
        """
        read_value = not read
        if type(email).__name__ == "_MailItem":
            email.UnRead = read_value
            email.Save()
        elif isinstance(email, dict):
            email["object"].UnRead = read_value
            email["object"].Save()

    def move_emails(
        self,
        account_name: str = None,
        source_folder: str = None,
        email_filter: str = None,
        target_folder: str = None,
    ) -> bool:
        """Move emails from source folder to target folder.

        Use of "account_name" is recommended if there are shared accounts in use.

        :param account_name: needs to be given if there are shared accounts in use,
         defaults to None
        :param source_folder: folder where source emails exist
        :param email_filter: how to filter email, default no filter,
         ie. all emails in folder
        :param target_folder: folder where emails are moved into
        :return: True if move operation was success, False if not

        Example:

        .. code-block:: robotframework

            # moving messages from Inbox to target_folder
            Move Emails
            ...    target_folder=Processed Invoices
            ...    email_filter=[Subject]='incoming invoice'

            # moving messages from source_folder to target_folder
            Move Emails
            ...    source_folder=Incoming Invoices
            ...    target_folder=Processed Invoices
            ...    email_filter=[Subject]='incoming invoice'
        """
        if not target_folder:
            raise AttributeError("Can't move emails without target_folder")
        folder = self._get_folder(account_name, source_folder)
        folder_messages = folder.Items if folder else []
        if folder_messages and email_filter:
            try:
                folder_messages = folder_messages.Restrict(email_filter)
            except Exception:
                raise AttributeError(  # pylint: disable=raise-missing-from
                    "Invalid email filter '%s'" % email_filter
                )
        if not folder_messages:
            self.logger.warning("Did not find emails to move")
            return False
        tf = self._get_folder(account_name, target_folder)
        if not tf or tf.Name != target_folder:
            self.logger.warning("Did not find target folder")
            return False
        self.logger.info("Found %d emails to move", len(folder_messages))
        self.logger.info("Found target folder: %s", tf.Name)
        for m in folder_messages:
            m.UnRead = False
            m.Move(tf)
            m.Save()
        return True

    def _mail_item_to_dict(self, mail_item):
        mi = mail_item
        response = {
            "Sender": self._get_sender_email_address(mi),
            "To": [],
            "CC": [],
            "BCC": [],
            "Subject": mi.Subject,
            "Body": mi.Body,
            "Attachments": [
                {"filename": a.FileName, "size": a.Size, "item": a}
                for a in mi.Attachments
            ],
            "Size": mi.Size,
            "object": mi,
        }
        rt = getattr(mail_item, "ReceivedTime", "<UNKNOWN>")
        response["ReceivedTime"] = rt.isoformat() if rt != "<UNKNOWN>" else rt
        response["ReceivedTimestamp"] = (
            datetime(
                rt.year, rt.month, rt.day, rt.hour, rt.minute, rt.second
            ).timestamp()
            if rt
            else None
        )
        so = getattr(mail_item, "SentOn", "<UNKNOWN>")
        response["SentOn"] = so.isoformat() if so != "<UNKNOWN>" else so
        self._handle_recipients(mi.Recipients, response)
        return response

    def _get_recipient_email_address(self, recipient):
        email_address = None
        try:
            email_address = recipient.AddressEntry.GetExchangeUser().PrimarySmtpAddress
        except Exception:  # pylint: disable=broad-except
            email_address = recipient.Address
        return email_address

    def _handle_recipients(self, recipients, response):
        for r in recipients:
            if r.Type == 1:
                response["To"].append(
                    {
                        "name": r.Name,
                        "email": self._get_recipient_email_address(r),
                    }
                )
            elif r.Type == 2:
                response["CC"].append(
                    {
                        "name": r.Name,
                        "email": self._get_recipient_email_address(r),
                    }
                )
            elif r.Type == 3:
                response["BCC"].append(
                    {
                        "name": r.Name,
                        "email": self._get_recipient_email_address(r),
                    }
                )

    def _get_sender_email_address(self, mail_item):
        mi = mail_item
        return (
            mi.Sender.GetExchangeUser().PrimarySmtpAddress
            if mi.SenderEmailType == "EX"
            else mi.SenderEmailAddress
        )

    def _address_entry_to_dict(self, address_entry):
        ae = address_entry
        return {"Name": ae.Name, "Address": ae.Address}
