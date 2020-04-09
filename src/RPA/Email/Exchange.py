import logging
from exchangelib import Credentials, Account, Message, Mailbox


class Exchange:
    """Library for interfacing with Microsoft Exchange Web Services (EWS).
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.credentials = None
        self.account = None

    def authorize(self, username, password, autodiscover=True):
        """Connect to Exchange account

        :param username: account username
        :param password: account password
        :param autodiscover: use autodiscover or not
        """
        self.credentials = Credentials(username, password)
        self.account = Account(
            username, credentials=self.credentials, autodiscover=autodiscover
        )

    def list_messages(self, count=100):
        """List messages in the account inbox. Order by descending
        received time.
        """
        # pylint: disable=no-member
        messages = []
        for item in self.account.inbox.all().order_by("-datetime_received")[:count]:
            messages.append(
                {
                    "subject": item.subject,
                    "sender": item.sender,
                    "datetime_received": item.datetime_received,
                }
            )
        return messages

    def send_message(
        self,
        recipients=None,
        cc_recipients=None,
        bcc_recipients=None,
        subject="",
        body="",
        save=False,
    ):
        """Keyword for sending message through connected Exchange account.

        Email addresses can be prefixed with `ex:` to indicate Exchange
        account address.


        :param recipients: list of email addresses, defaults to []
        :param cc_recipients: list of email addresses, defaults to []
        :param bcc_recipients: list of email addresses, defaults to []
        :param subject: message subject, defaults to ""
        :param body: message body, defaults to ""
        :param save: is sent message saved to Sent messages folder or not,
            defaults to False

        """
        if recipients is None:
            self.logger.warning("recipients is None - not sending message")
            return
        if cc_recipients is None:
            cc_recipients = []
        if bcc_recipients is None:
            bcc_recipients = []
        if not isinstance(recipients, list):
            recipients = [recipients]
        if not isinstance(cc_recipients, list):
            cc_recipients = [cc_recipients]
        if not isinstance(bcc_recipients, list):
            bcc_recipients = [bcc_recipients]

        self.logger.info(f"Sending message to {','.join(recipients)}")

        mail_recipients = []
        mail_cc = []
        mail_bcc = []

        mail_recipients = [
            Mailbox(email_address=p.split("ex:")[1]) if "ex:" in p else p
            for p in recipients
        ]
        mail_cc = [
            Mailbox(email_address=p.split("ex:")[1]) if "ex:" in p else p
            for p in cc_recipients
        ]
        mail_bcc = [
            Mailbox(email_address=p.split("ex:")[1]) if "ex:" in p else p
            for p in bcc_recipients
        ]
        m = Message(
            account=self.account,
            subject=subject,
            body=body,
            to_recipients=mail_recipients,
            cc_recipients=mail_cc,
            bcc_recipients=mail_bcc,
        )
        if save:
            m.folder = self.account.sent
            m.send_and_save()
        else:
            m.send()
