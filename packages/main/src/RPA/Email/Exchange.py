import datetime
import email
import logging
import re
import time
from email import policy  # pylint: disable=no-name-in-module
from enum import Enum
from multiprocessing import AuthenticationError
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

import pytz
from exchangelib import (
    DELEGATE,
    IMPERSONATION,
    OAUTH2,
    UTC,
    Account,
    Configuration,
    Credentials,
    FileAttachment,
    Folder,
    HTMLBody,
    Identity,
    ItemAttachment,
    Mailbox,
    Message,
    OAuth2AuthorizationCodeCredentials,
)
from exchangelib.folders import Inbox
from oauthlib.oauth2 import OAuth2Token

from RPA.Email.common import (
    OAuthConfig,
    OAuthMixin,
    OAuthProvider,
    counter_duplicate_path,
    NoRecipientsError,
)
from RPA.Robocorp.Vault import Vault
from RPA.Robocorp.utils import protect_keywords


EMAIL_CRITERIA_KEYS = {
    "subject": "subject",
    "subject_contains": "subject__contains",
    "body": "body",
    "body_contains": "body__contains",
    "sender": "sender",
    "sender_contains": "sender__contains",
    "before": "datetime_received__range",
    "after": "datetime_received__range",
    "between": "datetime_received__range",
    "category": "categories",
    "category_contains": "categories__contains",
    "importance": "importance",
}

lib_vault = Vault()


def mailbox_to_email_address(mailbox):
    return {
        "name": mailbox.name if hasattr(mailbox, "name") else "",
        "email_address": mailbox.email_address
        if hasattr(mailbox, "email_address")
        else "",
    }


class AccessType(Enum):
    """Authorization access type."""

    DELEGATE = DELEGATE
    IMPERSONATION = IMPERSONATION


class OAuth2Creds(OAuth2AuthorizationCodeCredentials):

    """OAuth2 auth code flow credentials wrapper supporting token state on refresh."""

    def __init__(
        self, *args, on_token_refresh: Callable, oauth_provider: OAuthConfig, **kwargs
    ):
        super().__init__(*args, **kwargs)
        # Additional behaviour to trigger during token refresh (when it expires), like
        #  saving the newly generated structure in the Vault.
        self._on_token_refresh = on_token_refresh
        self._token_url = oauth_provider.token_url
        self._scope = oauth_provider.scope

    def on_token_auto_refreshed(self, access_token: OAuth2Token):
        """Saves the newly obtained token internally and in the Vault."""
        super().on_token_auto_refreshed(access_token)
        self._on_token_refresh(access_token)

    @property
    def token_url(self) -> str:
        """Custom token URL coming from the OAuth2 provider settings."""
        return self._token_url

    @property
    def scope(self) -> List[str]:
        """Custom permissions list coming from the OAuth2 provider settings."""
        return self._scope.split()


class Exchange(OAuthMixin):
    """`Exchange` is a library for sending, reading, and deleting emails.
    `Exchange` is interfacing with Exchange Web Services (EWS).

    For more information about server settings, see
    `this Microsoft support article <https://support.microsoft.com/en-us/office/server-settings-you-ll-need-from-your-email-provider-c82de912-adcc-4787-8283-45a1161f3cc3>`_.

    **Examples**

    **Robot Framework**

    .. code-block:: robotframework

        *** Settings ***
        Library     RPA.Email.Exchange
        ...     vault_name=email_oauth_microsoft    vault_token_key=token
        ...     tenant=ztzvn.onmicrosoft.com  # your custom tenant here
        Task Setup      Ensure Auth

        *** Variables ***
        ${ACCOUNT}              ACCOUNT_NAME
        ${RECIPIENT_ADDRESS}    RECIPIENT
        ${IMAGES}               myimage.png
        ${ATTACHMENTS}          C:${/}files${/}mydocument.pdf

        *** Keywords ***
        Ensure Auth
            ${secrets} =    Get Secret    email_oauth_microsoft
            RPA.Email.Exchange.Authorize    ${ACCOUNT}
            ...    is_oauth=${True}  # use the OAuth2 auth code flow (required)
            ...    client_id=${secrets}[client_id]  # app ID
            ...    client_secret=${secrets}[client_secret]  # app password
            ...    token=${secrets}[token]  # token dict (access, refresh, scope etc.)

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
            ...    criterion=subject:'about my orders'
            ...    save_dir=${CURDIR}${/}savedir2
            FOR    ${msg}    IN    @{messages}
                Log Many    ${msg}
            END

        Task of moving messages
            Move Messages    criterion=subject:'about my orders'
            ...    source=INBOX/Processed Purchase Invoices/sub2
            ...    target=INBOX/Problems/sub1

    **Python**

    .. code-block:: python

        from RPA.Email.Exchange import Exchange
        from RPA.Robocorp.Vault import Vault

        vault_name = "email_oauth_microsoft"
        secrets = Vault().get_secret(vault_name)
        ex_account = "ACCOUNT_NAME"

        mail = Exchange(
            vault_name=vault_name,
            vault_token_key="token",
            tenant="ztzvn.onmicrosoft.com"
        )
        mail.authorize(
            username=ex_account,
            is_oauth=True,
            client_id=secrets["client_id"],
            client_secret=secrets["client_secret"],
            token=secrets["token"]
        )
        mail.send_message(
            recipients="RECIPIENT",
            subject="Message from RPA Python",
            body="RPA Python message body",
        )

    **OAuth2**

    The OAuth2 flow is the only way of authorizing at the moment as Microsoft disabled
    entirely the usage of passwords, even App Passwords. And since you have to work
    with tokens now and because this library has the capability to automatically
    refresh an expired token, please don't forget to initialize the library with the
    following parameters: `vault_name`, `vault_token_key` and `tenant`.

    Learn more on how to use the OAuth2 flow in this Portal robot
    `example-oauth-email <https://github.com/robocorp/example-oauth-email>`_.

    **About criterion parameter**

    Following table shows possible criterion keys that can be used to filter emails.
    There apply to all keywords which have ``criterion`` parameter.

    ================= ================
    Key               Effective search
    ================= ================
    subject           subject to match
    subject_contains  subject to contain
    body              body to match
    body_contains     body to contain
    sender            sender (from) to match
    sender_contains   sender (from) to contain
    before            received time before this time
    after             received time after this time
    between           received time between start and end
    category          categories to match
    category_contains categories to contain
    importance        importance to match
    ================= ================

    Keys `before`, `after` and `between` at the moment support two
    different timeformats either `%d-%m-%Y %H:%M` or `%d-%m-%Y`. These
    keys also support special string `NOW` which can be used especially
    together with keyword ``Wait for message  criterion=after:NOW``.

    When giving time which includes hours and minutes then the whole
    time string needs to be enclosed into single quotes.

    .. code-block:: bash

        before:25-02-2022
        after:NOW
        between:'31-12-2021 23:50 and 01-01-2022 00:10'

    Different criterion keys can be combined.

    .. code-block:: bash

        subject_contains:'new year' between:'31-12-2021 23:50 and 01-01-2022 00:10'

    Please **note** that all values in the criterion that contain spaces need
    to be enclosed within single quotes.

    In the following example the email `subject` is going to matched
    only against `new` not `new year`.

    .. code-block:: bash

        subject_contains:new year

    """  # noqa: E501

    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    ROBOT_LIBRARY_DOC_FORMAT = "REST"

    TO_PROTECT = ["authorize"] + OAuthMixin.TO_PROTECT

    def __init__(
        self,
        vault_name: Optional[str] = None,
        vault_token_key: Optional[str] = None,
        tenant: Optional[str] = None,
    ) -> None:
        # Init the OAuth2 support. (mandatory usage)
        self._tenant = tenant or "common"
        super().__init__(OAuthProvider.MICROSOFT, tenant=self._tenant)

        protect_keywords("RPA.Email.Exchange", self.TO_PROTECT)
        self.logger = logging.getLogger(__name__)

        self._vault_name = vault_name
        self._vault_token_key = vault_token_key

        self.credentials = None
        self.config = None
        self.account = None
        self._saved_attachments = []

    def _on_token_refresh(self, token: OAuth2Token):
        """Callable you can override in order to save the newly obtained token in a
        safe place.
        """
        if self._vault_name and self._vault_token_key:
            token = dict(token)
            self._sync_token_metadata(token)
            secret = lib_vault.get_secret(self._vault_name)
            secret[self._vault_token_key] = token
            lib_vault.set_secret(secret)
            self.logger.info(
                "OAuth2 token was refreshed in Vault %r as %r. (new expiry: %d)",
                self._vault_name,
                self._vault_token_key,
                token["expires_at"],
            )
        else:
            self.logger.warning(
                "OAuth2 token was refreshed but didn't get saved in Vault as well."
                " (import the library with `vault_name` and `vault_token_key` set in"
                " order to avoid this)"
            )

    def authorize(
        self,
        username: str,
        password: Optional[str] = None,
        autodiscover: bool = True,
        access_type: Union[AccessType, str] = AccessType.DELEGATE,
        server: Optional[str] = None,
        primary_smtp_address: Optional[str] = None,
        is_oauth: bool = False,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        token: Optional[dict] = None,
    ) -> None:
        """Connect to Exchange account

        :param username: account username
        :param password: account password (can be skipped with OAuth2)
        :param autodiscover: use autodiscover or set it off (on by default)
        :param access_type: default "DELEGATE", other option "IMPERSONATION"
        :param server: required for configuration setting (with `autodiscover` off)
        :param primary_smtp_address: by default set to username, but can be
            set to be different from username
        :param is_oauth: use the OAuth2 authorization code flow (instead of basic auth)
        :param client_id: registered application ID
        :param client_secret: registered application secret (password)
        :param token: contains access and refresh tokens, type, scope, expiry etc.
        """
        kwargs = {}
        kwargs["autodiscover"] = autodiscover
        access_type = (
            access_type
            if isinstance(access_type, AccessType)
            else AccessType(access_type.lower())
        )
        kwargs["access_type"] = access_type.value
        kwargs["primary_smtp_address"] = (
            primary_smtp_address if primary_smtp_address else username
        )
        if is_oauth:
            self.credentials = OAuth2Creds(
                on_token_refresh=self._on_token_refresh,
                oauth_provider=self._oauth_provider,
                tenant_id=self._tenant,
                identity=Identity(upn=username),
                client_id=client_id,
                client_secret=client_secret,
                # Contains at least a non-expired access token or non-revoked refresh
                #  one. (otherwise an authorization code should be present inside)
                access_token=OAuth2Token(params=token) if token else None,
            )
        else:
            if password is None:
                raise ValueError("A password should be provided with basic auth")
            self.credentials = Credentials(username, password)
        if server:
            self.config = Configuration(
                server=server,
                credentials=self.credentials,
                # Automatically detects authentication type based on the provided
                #  `credentials` object. (when not using OAuth2)
                auth_type=OAUTH2 if is_oauth else None,
            )
            kwargs["config"] = self.config
        else:
            kwargs["credentials"] = self.credentials

        if self.config and autodiscover:
            self.logger.warning(
                "Autodiscovery is left ON while using custom configuration, you may "
                "need to turn it OFF in order to use the custom setting."
            )
        self.account = Account(**kwargs)

    def list_messages(
        self,
        folder_name: Optional[str] = None,
        criterion: Optional[str] = None,
        contains: Optional[bool] = False,  # pylint: disable=unused-argument
        count: Optional[int] = 100,
        save_dir: Optional[str] = None,
        items_only: Optional[bool] = False,
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
        :param items_only: return only list of Message objects (instead of dictionaries)
        """
        # pylint: disable=no-member
        messages = []
        source_folder = self._get_folder_object(folder_name)
        if criterion:
            filter_dict = self._get_filter_key_value(criterion)
            items = source_folder.filter(**filter_dict)
        else:
            items = source_folder.all()
        if items_only:
            return items
        for item in items.order_by("-datetime_received")[:count]:
            attachments = []
            if save_dir and len(item.attachments) > 0:
                # NOTE(cmin764): Default `overwrite` param is assumed here.
                attachments = self._save_attachments(item, save_dir)
            messages.append(self._get_email_details(item, attachments))
        return messages

    def list_unread_messages(
        self,
        folder_name: Optional[str] = None,
        criterion: Optional[str] = None,
        contains: Optional[bool] = False,
        count: Optional[int] = 100,
        save_dir: Optional[str] = None,
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

    def _get_inbox_folder(
        self, folder_name: str, parent_folder: Optional[str] = None
    ) -> Inbox:
        if parent_folder is None or parent_folder is self.account.inbox:
            parent = self.account.inbox
        else:
            parent = self.account.inbox / parent_folder
        return parent / folder_name if folder_name else parent

    def send_message(
        self,
        recipients: Optional[Union[List[str], str]] = None,
        subject: Optional[str] = "",
        body: Optional[str] = "",
        attachments: Optional[Union[List[str], str]] = None,
        html: Optional[bool] = False,
        images: Optional[Union[List[str], str]] = None,
        cc: Optional[Union[List[str], str]] = None,
        bcc: Optional[Union[List[str], str]] = None,
        save: Optional[bool] = False,
    ) -> None:
        """Keyword for sending message through connected Exchange account.

        :param recipients: list of email addresses
        :param subject: message subject, defaults to ""
        :param body: message body, defaults to ""
        :param attachments: list of filepaths to attach, defaults to `None`
        :param html: if message content is in HTML, default `False`
        :param images: list of filepaths for inline use, defaults to `None`
        :param cc: list of email addresses
        :param bcc: list of email addresses
        :param save: is sent message saved to Sent messages folder or not,
            defaults to False

        Email addresses can be prefixed with ``ex:`` to indicate an Exchange
        account address.

        At least one target needs to exist for `recipients`, `cc` or `bcc`.
        """
        if not self.account:
            raise AuthenticationError("Not authorized to any Exchange account")
        recipients, cc, bcc, attachments, images = self._handle_message_parameters(
            recipients, cc, bcc, attachments, images
        )
        if not recipients and not cc and not bcc:
            raise NoRecipientsError(
                "At least one address is required for 'recipients', 'cc' or 'bcc' parameter"  # noqa: E501
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

        # TODO. The exchangelib does not seem to provide any straightforward way of
        # verifying if message was sent or not
        if save:
            m.folder = self.account.sent
            m.send_and_save()
        else:
            m.send()

    def send_reply_message(
        self,
        message: Union[Message, str],
        body: str,
        subject: str = None,
        reply_all: bool = False,
    ):
        """Send reply to a message.

        :param message: either Message object or ID of the message
         for the message which this is replying to
        :param body: message body for the reply
        :param subject: optional subject for the reply, defaults to None
        :param reply_all: if `True` then reply is sent to all recipients,
         defaults to False

        **Robot Framework example**

        .. code-block:: robotframework

            ${messages}=    List Messages    criterion=subject:'I have new query'
            FOR    ${m}    IN    @{messages}
                # Verifying that this is email that I want to reply to
                ${now}=    RPA.Calendar.Time Now   UTC  return_format=YYYY-MM-DD HH:mm
                ${received}=    Evaluate    str($m["datetime_received"])
                ${diff}=   RPA.Calendar.Time Difference In Minutes   ${received}  ${now}
                # message was received less than 5 minutes
                # and it came from the expected address
                IF    $diff < 5 and "${m}[sender]" == "mika@robocorp.com"
                    Send Reply Message
                    ...  ${m}[id]
                    ...  body=I totally agree
                END
            END
        """
        if isinstance(message, str):
            message_id = message
            message = self.account.inbox.get(id=message_id)  # pylint: disable=no-member
            if not isinstance(message, Message):
                raise ValueError(f"Could not get message by id '{message_id}'")
        if subject:
            new_subject = subject
        else:
            new_subject = (f"Re: {message.subject}")[:255]
        if reply_all:
            message.reply_all(subject=new_subject, body=body)
        else:
            message.reply(
                subject=new_subject, body=body, to_recipients=[message.author]
            )

    def _handle_message_parameters(self, recipients, cc, bcc, attachments, images):
        recipients = recipients or []
        cc = cc or []
        bcc = bcc or []
        attachments = attachments or []
        images = images or []
        if not isinstance(recipients, list):
            recipients = recipients.split(",")
        if not isinstance(cc, list):
            cc = cc.split(",")
        if not isinstance(bcc, list):
            bcc = bcc.split(",")
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

    def create_folder(self, folder_name: str, parent_folder: Optional[str] = None):
        """Create email folder.

        :param folder_name: name for the new folder (required)
        :param parent_folder: name for the parent folder, by default INBOX
        """
        parent = self._get_inbox_folder(folder_name, parent_folder)
        self.logger.info("Create folder %r", folder_name)
        new_folder = Folder(parent=parent, name=folder_name)
        new_folder.save()

    def delete_folder(self, folder_name: str, parent_folder: Optional[str] = None):
        """Delete email folder.

        :param folder_name: current folder name (required)
        :param parent_folder: name for the parent folder, by default INBOX
        """
        folder_to_delete = self._get_inbox_folder(folder_name, parent_folder)
        self.logger.info("Delete folder %r", folder_name)
        folder_to_delete.delete()

    def rename_folder(
        self,
        oldname: str,
        newname: str,
        parent_folder: Optional[str] = None,
    ):
        """Rename email folder

        :param oldname: current folder name
        :param newname: new name for the folder
        :param parent_folder: name for the parent folder, by default INBOX
        :return: True if operation was successful, False if not
        """
        parent = self._get_inbox_folder("", parent_folder)
        self.logger.info("Rename folder %r to %r", oldname, newname)
        items = self._get_inbox_folder(oldname, parent_folder).all()
        old_folder = Folder(parent=parent, name=oldname)
        old_folder.name = newname
        old_folder.save()
        items.move(to_folder=parent / newname)
        self.delete_folder(oldname, parent_folder)

    def empty_folder(
        self,
        folder_name: str,
        parent_folder: Optional[str] = None,
        delete_sub_folders: Optional[bool] = False,
    ):
        """Empty email folder of all items

        :param folder_name: current folder name (required)
        :param parent_folder: name for the parent folder, by default INBOX
        :param delete_sub_folders: delete sub folders or not, by default False
        :return: True if operation was successful, False if not
        """
        if parent_folder is None:
            empty_folder = self._get_folder_object(folder_name)
        else:
            empty_folder = self._get_folder_object(f"{parent_folder} / {folder_name}")
        self.logger.info("Empty folder %r", empty_folder)
        empty_folder.empty(delete_sub_folders=delete_sub_folders)

    def move_messages(
        self,
        criterion: Optional[str] = "",
        source: Optional[str] = None,
        target: Optional[str] = None,
        contains: Optional[bool] = False,  # pylint: disable=unused-argument
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
        filter_dict = self._get_filter_key_value(criterion)
        items = source_folder.filter(**filter_dict)
        if items and items.count() > 0:
            items.move(to_folder=target_folder)
            return True
        else:
            self.logger.warning("No items match criterion '%s'", criterion)
            return False

    def move_message(
        self,
        msg: Optional[dict],
        target: Optional[str],
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
                folder_object /= folder.strip()
            else:
                folder_object = folder

        return folder_object

    def _get_filter_key_value(self, criterion):
        regex1 = rf"({':|'.join(EMAIL_CRITERIA_KEYS)}:|or|and)'(.*?)'"
        regex2 = rf"({':|'.join(EMAIL_CRITERIA_KEYS)}:|or|and)(\S*)\s*"
        parts = re.findall(regex1, criterion, re.IGNORECASE)
        valid_filters = {}
        for part in parts:
            res = self._parse_email_criteria(part)
            if not res or len(res) != 2:
                continue
            self.logger.debug("First regex pass: %s %s", res[0], res[1])
            if res[0] not in valid_filters.keys():
                valid_filters[res[0]] = res[1]
        parts = re.findall(regex2, criterion, re.IGNORECASE)
        for part in parts:
            res = self._parse_email_criteria(part)
            if not res or len(res) != 2:
                continue
            self.logger.debug("Second regex pass: %s %s", res[0], res[1])
            if res[0] not in valid_filters.keys():
                valid_filters[res[0]] = res[1]
        if criterion and criterion != "" and len(valid_filters) == 0:
            raise KeyError("Invalid criterion '%s'" % criterion)
        self.logger.info(
            "Using filter: %s",
            ",".join(["{}:{}".format(k, v) for k, v in valid_filters.items()]),
        )
        return valid_filters

    def _parse_email_criteria(self, part):
        original_key, value = part
        original_key = original_key.replace(":", "")
        if original_key in ["and", "or", "contains"]:
            # Note. Not implemented yet
            return None
        key = None
        if original_key in EMAIL_CRITERIA_KEYS.keys():
            key = EMAIL_CRITERIA_KEYS[original_key]
        else:
            raise KeyError("Unknown email criteria key '%s'" % original_key)

        if value.startswith("'") and value.endswith("'"):
            value = value[1:-1]

        value = self._handle_specific_keys(original_key, value)
        self.logger.debug("Returning parsed criteria (%s, %s)", key, value)
        return key, value

    def _parse_date_from_string(self, date_string):
        date = None
        if date_string.upper() == "NOW":
            right_now = datetime.datetime.now()
            return right_now.astimezone(pytz.utc)
        try:
            date = datetime.datetime.strptime(date_string, "%d-%m-%Y %H:%M")
            return self._date_for_exchange(date)
        except ValueError:
            pass
        try:
            date = datetime.datetime.strptime(date_string, "%d-%m-%Y")
            return self._date_for_exchange(date)
        except ValueError:
            pass
        return date

    def _date_for_exchange(self, date):
        return datetime.datetime(
            date.year,
            date.month,
            date.day,
            date.hour,
            date.minute,
            tzinfo=UTC,
        )

    def _handle_specific_keys(self, key, value):
        if key.upper() == "BEFORE":
            start = datetime.datetime(1972, 1, 1, tzinfo=UTC)
            end = self._parse_date_from_string(value)
            value = (start, end)
        if key.upper() == "AFTER":
            start = self._parse_date_from_string(value)
            end = datetime.datetime(2050, 1, 1, tzinfo=UTC)
            value = (start, end)
        if key.upper() == "BETWEEN":
            ranges = value.upper().split(" AND ")
            if len(ranges) == 2:
                start = self._parse_date_from_string(ranges[0])
                end = self._parse_date_from_string(ranges[1])
                value = (start, end)
            else:
                return None
        if key.upper() == "IMPORTANCE":
            try:
                value = value.capitalize()
            except ValueError:
                return None
        return value

    def wait_for_message(
        self,
        criterion: Optional[str] = "",
        timeout: Optional[float] = 5.0,
        interval: Optional[float] = 1.0,
        contains: Optional[bool] = False,  # pylint: disable=unused-argument
        save_dir: Optional[str] = None,
    ) -> Any:
        """Wait for email matching `criterion` to arrive into INBOX.

        :param criterion: wait for message matching criterion
        :param timeout: total time in seconds to wait for email, defaults to 5.0
        :param interval: time in seconds for new check, defaults to 1.0 (minimum)
        :param contains: if matching should be done using `contains` matching
         and not `equals` matching, default `False` is means `equals` matching
         THIS PARAMETER IS DEPRECATED AS OF rpaframework 12.9.0
        :param save_dir: set to path where attachments should be saved,
         default None (attachments are not saved)
        :return: list of messages
        """
        self.logger.info("Wait for messages")
        end_time = time.time() + float(timeout)
        filter_dict = self._get_filter_key_value(criterion)
        items = None
        # minimum interval is 1.0 seconds
        interval = max(interval, 1.0)
        while time.time() < end_time:
            items = self.account.inbox.filter(**filter_dict)  # pylint: disable=E1101
            if items.count() > 0:
                break
            time.sleep(interval)
        messages = []
        for item in items:
            attachments = []
            if save_dir and len(item.attachments) > 0:
                # NOTE(cmin764): Default `overwrite` param is assumed here.
                attachments = self._save_attachments(item, save_dir)
            messages.append(self._get_email_details(item, attachments))

        if len(messages) == 0:
            self.logger.info("Did not receive any matching items")
        return messages

    def _save_attachments(
        self,
        item,
        save_dir: str,
        attachments_from_emls: bool = False,
        overwrite: bool = False,
    ):
        self._saved_attachments = self._saved_attachments or []
        incoming_items = item.attachments if hasattr(item, "attachments") else item

        for attachment in incoming_items:
            self.logger.debug("Attachment type: %s", type(attachment))
            local_path = Path(save_dir) / attachment.name
            if not overwrite:
                local_path = counter_duplicate_path(local_path)

            if isinstance(attachment, FileAttachment):
                with open(local_path, "wb") as stream_out, attachment.fp as stream_in:
                    buffer = stream_in.read(1024)
                    while buffer:
                        stream_out.write(buffer)
                        buffer = stream_in.read(1024)
            elif isinstance(attachment, ItemAttachment):
                with open(local_path, "wb") as message_out:
                    message_out.write(attachment.item.mime_content)
                if attachments_from_emls:
                    self._save_attachments(
                        attachment.item,
                        save_dir,
                        attachments_from_emls=False,
                        overwrite=overwrite,
                    )
            else:
                self.logger.warning(
                    "Unrecognized attachment type: %s", type(attachment)
                )
                return self._saved_attachments

            self.logger.info("Attachment saved to: %s", local_path)
            self._saved_attachments.append(
                self._new_attachment_dictionary(attachment, local_path)
            )

        return self._saved_attachments

    @staticmethod
    def _new_attachment_dictionary(
        attachment: Union[FileAttachment, ItemAttachment], local_path: Path
    ) -> Dict:
        return {
            "name": attachment.name,
            "content_type": attachment.content_type,
            "size": attachment.size,
            "is_contact_photo": getattr(attachment, "is_contact_photo", False),
            "local_path": str(local_path),
        }

    def _get_email_details(self, item, attachments):
        return {
            "subject": item.subject,
            "sender": mailbox_to_email_address(item.sender),
            "datetime_received": item.datetime_received,
            "folder": str(self._get_folder_object(item.folder)),
            "body": item.body,
            "text_body": item.text_body,
            "received_by": mailbox_to_email_address(item.received_by),
            "cc_recipients": [mailbox_to_email_address(cc) for cc in item.cc_recipients]
            if item.cc_recipients
            else [],
            "bcc_recipients": [
                mailbox_to_email_address(bcc) for bcc in item.bcc_recipients
            ]
            if item.bcc_recipients
            else [],
            "is_read": item.is_read,
            "importance": item.importance,
            "message_id": item.message_id,
            "size": item.size,
            "categories": item.categories,
            "has_attachments": len(item.attachments) > 0,
            "attachments": attachments,
            "attachments_object": item.attachments,
            "id": item.id,
            "changekey": item.changekey,
            "mime_content": item.mime_content,
        }

    def save_attachments(
        self,
        message: Union[dict, str],
        save_dir: Optional[str] = None,
        attachments_from_emls: bool = False,
        overwrite: bool = False,
    ) -> list:
        """Save attachments from message into given directory.

        :param message: dictionary or .eml file path containing message details
        :param save_dir: file path where attachments will be saved
        :param attachments_from_emls: pass `True` if the attachment is an EML file (for
            saving attachments from that EML file instead), `False` otherwise (default)
        :param overwrite: overwrite existing downloaded attachments with the same name
            if set to `True`, `False` otherwise (default)
        :return: list of saved attachments

        Example:

        .. code:: robotframework

            ${messages} =    List Messages
            FOR    ${msg}    IN    @{messages}
                Save Attachments    ${msg}    %{ROBOT_ARTIFACTS}
                ...    attachments_from_emls=${True}
            END

            ${attachments} =    Save Attachments    ${CURDIR}${/}saved.eml
            ...    %{ROBOT_ARTIFACTS}    overwrite=${True}
        """  # noqa: E501
        self._saved_attachments = []
        if isinstance(message, dict):
            return self._save_attachments(
                message["attachments_object"],
                save_dir,
                attachments_from_emls=attachments_from_emls,
                overwrite=overwrite,
            )
        else:
            # extract attachments from .eml file
            absolute_filepath = Path(message).resolve()
            if absolute_filepath.suffix != ".eml":
                raise ValueError("Filename extension needs to be '.eml'")
            return self._save_attachments_from_file(
                message, save_dir, overwrite=overwrite
            )

    def _save_attachments_from_file(
        self, filename: str, save_dir: str, *, overwrite: bool
    ):
        """
        Try to extract the attachments from given .eml file
        """
        # ensure that an output dir exists
        attachments = []
        with open(filename, "r") as f:  # pylint: disable=unspecified-encoding
            msg = email.message_from_file(  # pylint: disable=no-member
                f, policy=policy.default
            )
            for attachment in msg.iter_attachments():
                output_filename = attachment.get_filename()
                # If no attachments are found, skip this file
                if output_filename:
                    local_path = Path(save_dir) / output_filename
                    if not overwrite:
                        local_path = counter_duplicate_path(local_path)
                    with open(local_path, "wb") as of:
                        payload = attachment.get_payload(decode=True)
                        of.write(payload)
                        attachments.append(
                            {
                                "name": output_filename,
                                "content_type": None,
                                "size": len(payload),
                                "is_contact_photo": None,
                                "local_path": str(local_path),
                            }
                        )
            if len(attachments) == 0:
                self.logger.warning("No attachment found for file %s!", f.name)
        return attachments

    def save_message(self, message: dict, filename: str):
        """Save email as .eml file.

        :param message: dictionary containing message details
        :param filename: name of the file to save message into
        """
        absolute_filepath = Path(filename).resolve()
        if absolute_filepath.suffix != ".eml":
            raise ValueError("Filename extension needs to be '.eml'")
        with open(absolute_filepath, "wb") as message_out:
            message_out.write(message["mime_content"])
