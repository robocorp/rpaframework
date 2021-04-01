import logging
import os
from pathlib import Path
import time
from typing import Any

from exchangelib import (
    Account,
    Configuration,
    Credentials,
    DELEGATE,
    EWSDateTime,
    EWSTimeZone,
    FileAttachment,
    Folder,
    HTMLBody,
    IMPERSONATION,
    Mailbox,
    Message,
)


def mailbox_to_email_address(mailbox):
    return {
        "name": mailbox.name,
        "email_address": mailbox.email_address,
    }


class Exchange:
    """`Exchange` is a library for sending, reading, and deleting emails.
    `Exchange` is interfacing with Exchange Web Services (EWS).

    For more information about server settings, see
    `this Microsoft support article <https://support.microsoft.com/en-us/office/server-settings-you-ll-need-from-your-email-provider-c82de912-adcc-4787-8283-45a1161f3cc3>`_.

    **Examples**

    **Robot Framework**

    .. code-block:: robotframework

        *** Settings ***
        Library     RPA.Email.Exchange
        Task Setup  Authorize  username=${ACCOUNT}  password=${PASSWORD}

        *** Variables ***
        ${ACCOUNT}              ACCOUNT_NAME
        ${PASSWORD}             ACCOUNT_PASSWORD
        ${RECIPIENT_ADDRESS}    RECIPIENT
        ${IMAGES}               myimage.png
        ${ATTACHMENTS}          C:${/}files${/}mydocument.pdf

        *** Tasks ***
        Task of sending email
            Send Message  recipients=${RECIPIENT_ADDRESS}
            ...           subject=Exchange Message from RPA Robot
            ...           body=<p>Exchange RPA Robot message body<br><img src='myimage.png'/></p>
            ...           save=${TRUE}
            ...           html=${TRUE}
            ...           images=${IMAGES}
            ...           cc=EMAIL_ADDRESS
            ...           bcc=EMAIL_ADDRESS
            ...           attachments=${ATTACHMENTS}

        Task of listing messages
            # Attachments are saved specifically with a keyword Save Attachments
            ${messages}=    List Messages
            FOR    ${msg}    IN    @{messages}
                Log Many    ${msg}
                ${attachments}=    Run Keyword If    "${msg}[subject]"=="about my orders"
                ...    Save Attachments
                ...    ${msg}
                ...    save_dir=${CURDIR}${/}savedir
            END
            # Using save_dir all attachments in listed messages are saved
            ${messages}=    List Messages
            ...    INBOX/Problems/sub1
            ...    criterion=subject:about my orders
            ...    save_dir=${CURDIR}${/}savedir2
            FOR    ${msg}    IN    @{messages}
                Log Many    ${msg}
            END

        Task of moving messages
            Move Messages    criterion=subject:about my orders
            ...    source=INBOX/Processed Purchase Invoices/sub2
            ...    target=INBOX/Problems/sub1

    **Python**

    .. code-block:: python

        from RPA.Email.Exchange import Exchange

        ex_account = "ACCOUNT_NAME"
        ex_password = "ACCOUNT_PASSWORD"

        mail = Exchange()
        mail.authorize(username=ex_account, password=ex_password)
        mail.send_message(
            recipients="RECIPIENT",
            subject="Message from RPA Python",
            body="RPA Python message body",
        )
    """  # noqa: E501

    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    ROBOT_LIBRARY_DOC_FORMAT = "REST"

    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)
        self.credentials = None
        self.config = None
        self.account = None

    def authorize(
        self,
        username: str,
        password: str,
        autodiscover: bool = True,
        access_type: str = "DELEGATE",
        server: str = None,
        primary_smtp_address: str = None,
    ) -> None:
        """Connect to Exchange account

        :param username: account username
        :param password: account password
        :param autodiscover: use autodiscover or set it off
        :param accesstype: default "DELEGATE", other option "IMPERSONATION"
        :param server: required for configuration options
        :param primary_smtp_address: by default set to username, but can be
            set to be different than username
        """
        kwargs = {}
        kwargs["autodiscover"] = autodiscover
        kwargs["access_type"] = (
            DELEGATE if access_type.upper() == "DELEGATE" else IMPERSONATION
        )
        kwargs["primary_smtp_address"] = (
            primary_smtp_address if primary_smtp_address else username
        )
        self.credentials = Credentials(username, password)
        if server:
            self.config = Configuration(server=server, credentials=self.credentials)
            kwargs["config"] = self.config
        else:
            kwargs["credentials"] = self.credentials

        self.account = Account(**kwargs)

    def list_messages(
        self,
        folder_name: str = None,
        criterion: str = None,
        contains: bool = False,
        count: int = 100,
        save_dir: str = None,
    ) -> list:
        """List messages in the account inbox. Order by descending
        received time.

        :param folder_name: name of the email folder, default INBOX
        :param criterion: list messages matching criterion
        :param contains: if matching should be done using `contains` matching
         and not `equals` matching, default `False` is means `equals` matching
        :param count: number of messages to list
        :param save_dir: set to path where attachments should be saved,
         default None (attachments are not saved)
        """
        # pylint: disable=no-member
        messages = []
        source_folder = self._get_folder_object(folder_name)
        if criterion:
            filter_dict = self._get_filter_key_value(criterion, contains)
            items = source_folder.filter(**filter_dict)
        else:
            items = source_folder.all()
        for item in items.order_by("-datetime_received")[:count]:
            attachments = []
            if save_dir and len(item.attachments) > 0:
                attachments = self._save_attachments(item, save_dir)
            messages.append(self._get_email_details(item, attachments))
        return messages

    def list_unread_messages(
        self,
        folder_name: str = None,
        criterion: str = None,
        contains: bool = False,
        count: int = 100,
        save_dir: str = None,
    ) -> list:
        """List unread messages in the account inbox. Order by descending
        received time.

        :param folder_name: name of the email folder, default INBOX
        :param criterion: list messages matching criterion
        :param contains: if matching should be done using `contains` matching
         and not `equals` matching, default `False` is means `equals` matching
        :param count: number of messages to list
        :param save_dir: set to path where attachments should be saved,
         default None (attachments are not saved)
        """
        messages = self.list_messages(folder_name, criterion, contains, count, save_dir)
        return [m for m in messages if not m["is_read"]]

    def _get_all_items_in_folder(self, folder_name=None, parent_folder=None) -> list:
        if parent_folder is None or parent_folder is self.account.inbox:
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

        Email addresses can be prefixed with ``ex:`` to indicate an Exchange
        account address.

        Recipients is a `required` parameter.
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
        if parent_folder is None or parent_folder is self.account.inbox:
            parent = self.account.inbox
        else:
            parent = self.account.inbox / parent_folder / folder_name
        self.logger.info(
            "Create folder '%s'",
            folder_name,
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
        if parent_folder is None or parent_folder is self.account.inbox:
            folder_to_delete = self.account.inbox / folder_name
        else:
            folder_to_delete = self.account.inbox / parent_folder / folder_name
        self.logger.info(
            "Delete folder  '%s'",
            folder_name,
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
        if parent_folder is None or parent_folder is self.account.inbox:
            parent = self.account.inbox
        else:
            parent = self.account.inbox / parent_folder
        self.logger.info(
            "Rename folder '%s' to '%s'",
            oldname,
            newname,
        )
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
        if parent_folder is None:
            empty_folder = self._get_folder_object(folder_name)
        else:
            empty_folder = self._get_folder_object(f"{parent_folder} / {folder_name}")
        self.logger.info("Empty folder '%s'", empty_folder)
        empty_folder.empty(delete_sub_folders=delete_sub_folders)

    def move_messages(
        self,
        criterion: str = "",
        source: str = None,
        target: str = None,
        contains: bool = False,
    ) -> bool:
        """Move message(s) from source folder to target folder

        :param criterion: move messages matching this criterion
        :param source: source folder
        :param target: target folder
        :param contains: if matching should be done using `contains` matching
         and not `equals` matching, default `False` is means `equals` matching
        :return: boolean result of operation, True if 1+ items were moved else False

        Criterion examples:

        - subject:my message subject
        - body:something in body
        - sender:sender@domain.com
        """
        source_folder = self._get_folder_object(source)
        target_folder = self._get_folder_object(target)
        if source_folder == target_folder:
            raise KeyError("Source folder is same as target folder")
        filter_dict = self._get_filter_key_value(criterion, contains)
        items = source_folder.filter(**filter_dict)
        if items and items.count() > 0:
            items.move(to_folder=target_folder)
            return True
        else:
            self.logger.warning("No items match criterion '%s'", criterion)
            return False

    def move_message(
        self,
        msg: dict,
        target: str,
    ):
        """Move a message into target folder

        :param msg: dictionary of the message
        :param target: path to target folder
        :raises AttributeError: if `msg` is not a dictionary containing
         `id` and `changekey` attributes

        Example:

        .. code-block:: robotframework

            ${messages}=    List Messages
            ...    INBOX
            ...    criterion=subject:about my orders
            FOR    ${msg}    IN    @{messages}
                Run Keyword If    "${msg}[sender][email_address]"=="${priority_account}"
                ...    Move Message    ${msg}    target=INBOX / Problems / priority
            END
        """
        if not all(k in msg for k in ["id", "changekey"]):
            raise AttributeError(
                "Move Message keyword expects message dictionary "
                'containing "id" and "changekey" attributes'
            )
        message_id = [(msg["id"], msg["changekey"])]
        target_folder = self._get_folder_object(target)
        self.account.bulk_move(ids=message_id, to_folder=target_folder)

    def _get_folder_object(self, folder_name):
        if not folder_name:
            return self.account.inbox
        folders = folder_name.split("/")
        if "inbox" in folders[0].lower():
            folders[0] = self.account.inbox
        folder_object = None
        for folder in folders:
            if folder_object:
                folder_object = folder_object / folder.strip()
            else:
                folder_object = folder
        return folder_object

    def _get_filter_key_value(self, criterion, contains):
        if criterion.startswith("subject:"):
            search_key = "subject"
        elif criterion.startswith("body:"):
            search_key = "body"
        elif criterion.startswith("sender:"):
            search_key = "sender"
        else:
            raise KeyError("Unknown criterion for filtering items '%s'" % criterion)
        if contains:
            search_key += "__contains"
        _, search_val = criterion.split(":", 1)
        return {search_key: search_val}

    def wait_for_message(
        self,
        criterion: str = "",
        timeout: float = 5.0,
        interval: float = 1.0,
        contains: bool = False,
        save_dir: str = None,
    ) -> Any:
        """Wait for email matching `criterion` to arrive into INBOX.

        :param criterion: wait for message matching criterion
        :param timeout: total time in seconds to wait for email, defaults to 5.0
        :param interval: time in seconds for new check, defaults to 1.0
        :param contains: if matching should be done using `contains` matching
         and not `equals` matching, default `False` is means `equals` matching
        :param save_dir: set to path where attachments should be saved,
         default None (attachments are not saved)
        :return: list of messages
        """
        self.logger.info("Wait for messages")
        end_time = time.time() + float(timeout)
        filter_dict = self._get_filter_key_value(criterion, contains)
        items = None
        tz = EWSTimeZone.localzone()
        right_now = tz.localize(EWSDateTime.now())  # pylint: disable=E1101
        while time.time() < end_time:
            items = self.account.inbox.filter(  # pylint: disable=E1101
                **filter_dict, datetime_received__gte=right_now
            )
            if items.count() > 0:
                break
            time.sleep(interval)
        messages = []
        for item in items:
            attachments = []
            if save_dir and len(item.attachments) > 0:
                attachments = self._save_attachments(item, save_dir)
            messages.append(self._get_email_details(item, attachments))

        if len(messages) == 0:
            self.logger.info("Did not receive any matching items")
        return messages

    def _save_attachments(self, item, save_dir):
        attachments = []
        incoming_items = item.attachments if hasattr(item, "attachments") else item
        for attachment in incoming_items:
            if isinstance(attachment, FileAttachment):
                local_path = os.path.join(save_dir, attachment.name)
                with open(local_path, "wb") as f, attachment.fp as fp:
                    buffer = fp.read(1024)
                    while buffer:
                        f.write(buffer)
                        buffer = fp.read(1024)
                self.logger.info("Attachment saved to: %s", local_path)
                attachments.append(
                    {
                        "name": attachment.name,
                        "content_type": attachment.content_type,
                        "size": attachment.size,
                        "is_contact_photo": attachment.is_contact_photo,
                        "local_path": local_path,
                    }
                )
        return attachments

    def _get_email_details(self, email, attachments):
        return {
            "subject": email.subject,
            "sender": mailbox_to_email_address(email.sender),
            "datetime_received": email.datetime_received,
            "folder": str(self._get_folder_object(email.folder)),
            "body": email.body,
            "text_body": email.text_body,
            "received_by": mailbox_to_email_address(email.received_by),
            "cc_recipients": [
                mailbox_to_email_address(cc) for cc in email.cc_recipients
            ]
            if email.cc_recipients
            else [],
            "bcc_recipients": [
                mailbox_to_email_address(bcc) for bcc in email.bcc_recipients
            ]
            if email.bcc_recipients
            else [],
            "is_read": email.is_read,
            "importance": email.importance,
            "message_id": email.message_id,
            "size": email.size,
            "categories": email.categories,
            "attachments": attachments,
            "attachments_object": email.attachments,
            "id": email.id,
            "changekey": email.changekey,
        }

    def save_attachments(self, message: dict, save_dir: str = None) -> list:
        """Save attachments in message into given directory

        :param message: dictionary containing message details
        :param save_dir: filepath where attachments will be saved
        :return: list of saved attachments
        """
        return self._save_attachments(message["attachments_object"], save_dir)
