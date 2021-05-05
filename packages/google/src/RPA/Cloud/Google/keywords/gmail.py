import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from typing import Optional


from . import LibraryContext, keyword


class GmailKeywords(LibraryContext):
    """Class for Google Gmail API

    **Note:** The Gmail API does not work with _service accounts_

    Following steps are needed to authenticate and use the service:

    1. enable Drive API in the Cloud Platform project (GCP)
    2. create OAuth credentials so API can be authorized (download ``credentials.json``
       which is needed to initialize service)
    3. necessary authentication scopes and credentials.json are needed
       to initialize service

    For more information about Google Gmail API link_.

    .. _link: https://developers.google.com/gmail/api
    """

    def __init__(self, ctx):
        super().__init__(ctx)
        self.service = None

    @keyword
    def init_gmail(
        self,
        service_account: str = None,
        credentials: str = None,
        use_robocorp_vault: Optional[bool] = None,
        scopes: list = None,
        token_file: str = None,
    ) -> None:
        """Initialize Google Gmail client

        :param service_account: file path to service account file
        :param credentials: file path to credentials file
        :param use_robocorp_vault: use credentials in `Robocorp Vault`
        :param scopes: list of extra authentication scopes
        :param token_file: file path to token file
        """
        gmail_scopes = ["gmail.send", "gmail.compose", "gmail.modify", "gmail.labels"]
        if scopes:
            gmail_scopes += scopes
        self.service = self.init_service(
            service_name="gmail",
            api_version="v1",
            scopes=gmail_scopes,
            service_account_file=service_account,
            credentials_file=credentials,
            use_robocorp_vault=use_robocorp_vault,
            token_file=token_file,
        )

    def create_message(
        self,
        to: str,
        subject: str,
        message_text: str,
        # attachments: list = None,
    ):
        """Create a message for an email.

        Args:
            to: Email address of the receiver.
            subject: The subject of the email message.
            message_text: The text of the email message.
            attachments: list of attachments to send

        Returns:
            An object containing a base64url encoded email object.
        """
        mimeMessage = MIMEMultipart()
        mimeMessage["to"] = to
        mimeMessage["subject"] = subject
        mimeMessage.attach(MIMEText(message_text, "plain"))

        return {"raw": base64.urlsafe_b64encode(mimeMessage.as_bytes()).decode()}

    @keyword
    def send_message(
        self,
        sender: str,
        to: str,
        subject: str,
        message_text: str,
        # attachments: list = None,
    ):
        """Send an email message.

        Args:
            sender: User's email address. The special value "me"
            can be used to indicate the authenticated user.
            message: Message to be sent.

        Returns:
            Sent Message.
        """

        message = self.create_message(to, subject, message_text)
        response = (
            self.service.users().messages().send(userId=sender, body=message).execute()
        )
        print("Message Id: %s" % response["id"])
        return response
