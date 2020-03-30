import logging

from RPA.core.msoffice import OfficeApplication


class Application(OfficeApplication):
    """Library for manipulating Outlook application."""

    def __init__(self):
        OfficeApplication.__init__(self, application_name="Outlook")
        self.logger = logging.getLogger(__name__)

    def send_message(
        self, recipients, subject, body, html_body=False, attachments=None
    ):
        """Send message with Outlook

        :param recipients: list of addresses
        :param subject: email subject
        :param body: email body
        :param html_body: True if body contains HTML, defaults to False
        :param attachments: list of filepaths to include in the email, defaults to []
        """
        attachments = attachments or []

        mail = self.app.CreateItem(0)
        mail.To = recipients
        mail.Subject = subject
        mail.Body = body

        if html_body:
            mail.HTMLBody = html_body

        # Add attachments
        if len(attachments) > 0:
            for attachment in attachments:
                mail.Attachments.Add(attachment)

        # Send the e-mail
        mail.Send()
