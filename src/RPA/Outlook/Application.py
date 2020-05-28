import logging
from pathlib import Path
import platform
from typing import Any

from RPA.core.msoffice import OfficeApplication

if platform.system() == "Windows":
    import pywintypes


class Application(OfficeApplication):
    """Library for manipulating Outlook application."""

    def __init__(self):
        OfficeApplication.__init__(self, application_name="Outlook")
        self.logger = logging.getLogger(__name__)

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
