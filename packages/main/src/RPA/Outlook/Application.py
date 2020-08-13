from datetime import datetime
import logging
from pathlib import Path
import platform
import time
from typing import Any


if platform.system() == "Windows":
    import pywintypes
    import win32com.client


class Application:
    # pylint: disable=C0301
    """Library for manipulating Outlook application.

    For more information: https://docs.microsoft.com/en-us/previous-versions/office/developer/office-2007/bb219950(v=office.12) # noqa: E501
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.app = None

        if platform.system() != "Windows":
            self.logger.warning(
                "Outlook application library requires Windows dependencies to work."
            )

    def open_application(
        self, visible: bool = False, display_alerts: bool = False
    ) -> None:
        """Open the Outlook application.

        :param visible: show window after opening
        :param display_alerts: show alert popups
        """
        self.app = win32com.client.gencache.EnsureDispatch("Outlook.Application")

        if hasattr(self.app, "Visible"):
            self.app.Visible = visible

        # show eg. file overwrite warning or not
        if hasattr(self.app, "DisplayAlerts"):
            self.app.DisplayAlerts = display_alerts

    def close_document(self, save_changes: bool = False) -> None:
        """Close the active document (if open)."""
        if self.app is not None:
            self.app.ActiveDocument.Close(save_changes)

    def quit_application(self, save_changes: bool = False) -> None:
        """Quit the application."""
        if self.app is not None:
            self.close_document(save_changes)
            self.app.Quit()
            self.app = None

    def send_message(
        self,
        recipients: Any,
        subject: str,
        body: str,
        html_body: bool = False,
        attachments: Any = None,
    ) -> bool:
        """Send message with Outlook

        :param recipients: list of addresses
        :param subject: email subject
        :param body: email body
        :param html_body: True if body contains HTML, defaults to False
        :param attachments: list of filepaths to include in the email, defaults to []
        :return: `True` if there were no errors
        """
        # pylint: disable=no-member
        attachments = attachments or []
        if not isinstance(recipients, list):
            recipients = recipients.split(",")
        if not isinstance(attachments, list):
            attachments = str(attachments).split(",")

        mailto = ";".join(recipients)

        mail = self.app.CreateItem(0)
        mail.To = mailto
        mail.Subject = subject
        mail.Body = body

        if html_body:
            mail.HTMLBody = html_body

        # Add attachments
        if len(attachments) > 0:
            filepath = None
            try:
                for attachment in attachments:
                    filepath = Path(attachment).absolute()
                    mail.Attachments.Add(str(filepath))
            except pywintypes.com_error:
                self.logger.error(
                    "Attachment error - problem with filepath: %s", filepath
                )
                return False

        # Send the email
        try:
            mail.Send()
            self.logger.debug("Email sent")
        except pywintypes.com_error as e:
            self.logger.error("Mail send failed: %s", str(e))
            return False
        return True

    def _message_to_dictionary(self, message):
        msg = dict()
        msg["Subject"] = getattr(message, "Subject", "<UNKNOWN>")
        rt = getattr(message, "ReceivedTime", "<UNKNOWN>")
        msg["ReceivedTime"] = rt.isoformat()
        msg["ReceivedTimeTimestamp"] = datetime(
            rt.year, rt.month, rt.day, rt.hour, rt.minute, rt.second
        ).timestamp()
        so = getattr(message, "SentOn", "<UNKNOWN>")
        msg["SentOn"] = so.isoformat()
        msg["EntryID"] = getattr(message, "EntryID", "<UNKNOWN>")
        se = getattr(message, "Sender", "<UNKNOWN>")
        if message.SenderEmailType == "EX":
            sender = se.GetExchangeUser().PrimarySmtpAddress
        else:
            sender = message.SenderEmailAddress
        msg["Sender"] = sender
        msg["Size"] = getattr(message, "Size", "<UNKNOWN>")
        msg["Body"] = getattr(message, "Body", "<UNKNOWN>")
        return msg

    def _is_message_too_old(self, message):
        now = datetime.now().timestamp()
        msg_time = message["ReceivedTimeTimestamp"]
        timediff = now - msg_time
        return timediff > 30.0

    def _check_for_matching(self, criterion, message):
        crit_key, crit_val = criterion.split(":", 1)
        crit_key = crit_key.upper()
        crit_val = crit_val.lower()
        match_found = None

        if crit_key.upper() == "SUBJECT" and crit_val in message["Subject"].lower():
            match_found = message
        elif crit_key.upper() == "SENDER" and crit_val in message["Sender"].lower():
            match_found = message
        elif crit_key.upper() == "BODY" and crit_val in message["Body"].lower():
            match_found = message

        return match_found

    def wait_for_message(
        self, criterion: str = None, timeout: float = 5.0, interval: float = 1.0
    ) -> Any:
        """Wait for email matching `criterion` to arrive into mailbox.

        Possible wait criterias are: SUBJECT, SENDER and BODY

        Examples:
            - wait_for_message('SUBJECT:rpa task calling', timeout=300, interval=10)

        :param criterion: message filter to wait for, defaults to ""
        :param timeout: total time in seconds to wait for email, defaults to 5.0
        :param interval: time in seconds for new check, defaults to 1.0
        :return: list of messages or False
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
                m = self._message_to_dictionary(msg)
                if self._is_message_too_old(m):
                    break
                else:
                    match_found = self._check_for_matching(criterion, m)
                    if match_found:
                        return match_found
            time.sleep(interval)
        raise AssertionError("Did not find matching message in the Outlook inbox")
