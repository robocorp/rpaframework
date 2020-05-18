from pathlib import Path
import logging
from exchangelib import Account, Credentials, FileAttachment, HTMLBody, Mailbox, Message


class Exchange:
    """Library for interfacing with Microsoft Exchange Web Services (EWS).
    """

    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)
        self.credentials = None
        self.account = None

    def authorize(
        self, username: str, password: str, autodiscover: bool = True
    ) -> None:
        """Connect to Exchange account

        :param username: account username
        :param password: account password
        :param autodiscover: use autodiscover or not
        """
        self.credentials = Credentials(username, password)
        self.account = Account(
            username, credentials=self.credentials, autodiscover=autodiscover
        )

    def list_messages(self, count: int = 100) -> list:
        """List messages in the account inbox. Order by descending
        received time.

        :param count: number of messages to list
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
        recipients: str = None,
        subject: str = "",
        body: str = "",
        attachments: str = None,
        html: bool = False,
        images: str = None,
        cc: str = None,
        bcc: str = None,
        save: bool = False,
    ):
        """Keyword for sending message through connected Exchange account.

        Email addresses can be prefixed with `ex:` to indicate Exchange
        account address.


        :param recipients: list of email addresses, defaults to []
        :param subject: message subject, defaults to ""
        :param body: message body, defaults to ""
        :param attachments: list of filepaths to attach, defaults to []
        :param html: if message content is in HTML, default `False`
        :param images: list of filepaths for inline use, defaults to []
        :param cc: list of email addresses, defaults to []
        :param bcc: list of email addresses, defaults to []
        :param save: is sent message saved to Sent messages folder or not,
            defaults to False
        """
        if recipients is None:
            self.logger.warning("recipients is None - not sending message")
            return
        recipients, cc, bcc, attachments, images = self._handle_message_parameters(
            recipients, cc, bcc, attachments, images
        )
        self.logger.info("Sending message to %s", ",".join(recipients))

        m = Message(
            account=self.account,
            subject=subject,
            body=body,
            to_recipients=recipients,
            cc_recipients=cc,
            bcc_recipients=bcc,
        )

        self._add_attachments_to_msg(attachments, m)
        self._add_images_inline_to_msg(images, html, body, m)

        if html:
            m.body = HTMLBody(body)
        else:
            m.body = body

        if save:
            m.folder = self.account.sent
            m.send_and_save()
        else:
            m.send()

    def _handle_message_parameters(self, recipients, cc, bcc, attachments, images):
        if cc is None:
            cc = []
        if bcc is None:
            bcc = []
        if not isinstance(recipients, list):
            recipients = [recipients]
        if not isinstance(cc, list):
            cc = [cc]
        if not isinstance(bcc, list):
            bcc = [bcc]
        if not isinstance(attachments, list):
            attachments = [attachments]
        if not isinstance(images, list):
            images = [images]
        recipients, cc, bcc = self._handle_recipients(recipients, cc, bcc)
        return recipients, cc, bcc, attachments, images

    def _handle_recipients(self, recipients, cc, bcc):
        recipients = [
            Mailbox(email_address=p.split("ex:")[1]) if "ex:" in p else p
            for p in recipients
        ]
        cc = [Mailbox(email_address=p.split("ex:")[1]) if "ex:" in p else p for p in cc]
        bcc = [
            Mailbox(email_address=p.split("ex:")[1]) if "ex:" in p else p for p in bcc
        ]
        return recipients, cc, bcc

    def _add_attachments_to_msg(self, attachments, msg):
        for attachment in attachments:
            with open(attachment, "rb") as f:
                atname = str(Path(attachment).name)
                fileat = FileAttachment(name=atname, content=f.read())
                msg.attach(fileat)

    def _add_images_inline_to_msg(self, images, html, body, msg):
        for image in images:
            with open(image, "rb") as f:
                imname = str(Path(image).name)
                fileat = FileAttachment(
                    name=imname, content=f.read(), content_id=imname
                )
                msg.attach(fileat)
                if html:
                    body = body.replace(imname, f"cid:{imname}")
