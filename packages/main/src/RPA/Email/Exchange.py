import logging
from pathlib import Path
from typing import Any

from exchangelib import (
    Account,
    Credentials,
    FileAttachment,
    Folder,
    HTMLBody,
    Mailbox,
    Message,
)


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

    def list_messages(self, count: int = 100, folder_name: str = None) -> list:
        """List messages in the account inbox. Order by descending
        received time.

        :param count: number of messages to list
        """
        # pylint: disable=no-member
        messages = []
        items = self._get_all_items_in_folder(folder_name)
        for item in items.order_by("-datetime_received")[:count]:
            messages.append(
                {
                    "subject": item.subject,
                    "sender": item.sender,
                    "datetime_received": item.datetime_received,
                }
            )
        return messages

    def _get_all_items_in_folder(self, folder_name=None, parent_folder=None) -> list:
        if parent_folder is None or parent_folder == self.account.inbox:
            target_folder = self.account.inbox / folder_name
        else:
            target_folder = self.account.inbox / parent_folder / folder_name
        return target_folder.all()

    def send_message(
        self,
        recipients: str,
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

        Recipients is ``required`` parameter.

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
        return True

    def _handle_message_parameters(self, recipients, cc, bcc, attachments, images):
        if cc is None:
            cc = []
        if bcc is None:
            bcc = []
        if attachments is None:
            attachments = []
        if images is None:
            images = []
        if not isinstance(recipients, list):
            recipients = recipients.split(",")
        if not isinstance(cc, list):
            cc = [cc]
        if not isinstance(bcc, list):
            bcc = [bcc]
        if not isinstance(attachments, list):
            attachments = str(attachments).split(",")
        if not isinstance(images, list):
            images = str(images).split(",")
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
            attachment = attachment.strip()
            with open(attachment, "rb") as f:
                atname = str(Path(attachment).name)
                fileat = FileAttachment(name=atname, content=f.read())
                msg.attach(fileat)

    def _add_images_inline_to_msg(self, images, html, body, msg):
        for image in images:
            image = image.strip()
            with open(image, "rb") as f:
                imname = str(Path(image).name)
                fileat = FileAttachment(
                    name=imname, content=f.read(), content_id=imname
                )
                msg.attach(fileat)
                if html:
                    body = body.replace(imname, f"cid:{imname}")

    def create_folder(self, folder_name: str = None, parent_folder: str = None) -> bool:
        """Create email folder

        :param folder_name: name for the new folder
        :param parent_folder: name for the parent folder, by default INBOX
        :return: True if operation was successful, False if not
        """
        if folder_name is None:
            raise KeyError("'folder_name' is required for create folder")
        if parent_folder is None or parent_folder == self.account.inbox:
            parent = self.account.inbox
        else:
            parent = self.account.inbox / parent_folder / folder_name
        self.logger.info(
            "Create folder '%s'", folder_name,
        )
        new_folder = Folder(parent=parent, name=folder_name)
        new_folder.save()

    def delete_folder(self, folder_name: str = None, parent_folder: str = None) -> bool:
        """Delete email folder

        :param folder_name: current folder name
        :param parent_folder: name for the parent folder, by default INBOX
        :return: True if operation was successful, False if not
        """
        if folder_name is None:
            raise KeyError("'folder_name' is required for delete folder")
        if parent_folder is None or parent_folder == self.account.inbox:
            folder_to_delete = self.account.inbox / folder_name
        else:
            folder_to_delete = self.account.inbox / parent_folder / folder_name
        self.logger.info(
            "Delete folder  '%s'", folder_name,
        )
        folder_to_delete.delete()

    def rename_folder(
        self, oldname: str = None, newname: str = None, parent_folder: str = None
    ) -> bool:
        """Rename email folder

        :param oldname: current folder name
        :param newname: new name for the folder
        :param parent_folder: name for the parent folder, by default INBOX
        :return: True if operation was successful, False if not
        """
        if oldname is None or newname is None:
            raise KeyError("'oldname' and 'newname' are required for rename folder")
        if parent_folder is None or parent_folder == self.account.inbox:
            parent = self.account.inbox
        else:
            parent = self.account.inbox / parent_folder
        self.logger.info(
            "Rename folder '%s' to '%s'", oldname, newname,
        )
        self.account.inbox.refresh()
        items = self._get_all_items_in_folder(oldname, parent_folder)
        old_folder = Folder(parent=parent, name=oldname)
        old_folder.name = newname
        old_folder.save()
        items.move(to_folder=parent / newname)
        self.delete_folder(oldname, parent_folder)

    def empty_folder(
        self,
        folder_name: str = None,
        parent_folder: str = None,
        delete_sub_folders: bool = False,
    ) -> bool:
        """Empty email folder of all items

        :param folder_name: current folder name
        :param parent_folder: name for the parent folder, by default INBOX
        :param delete_sub_folders: delete sub folders or not, by default False
        :return: True if operation was successful, False if not
        """
        if folder_name is None:
            raise KeyError("'folder_name' is required for empty folder")
        if parent_folder is None or parent_folder == self.account.inbox:
            empty_folder = self.account.inbox / folder_name
        else:
            empty_folder = self.account.inbox / parent_folder / folder_name
        self.logger.info("Empty folder '%s'", folder_name)
        empty_folder.empty(delete_sub_folders=delete_sub_folders)
