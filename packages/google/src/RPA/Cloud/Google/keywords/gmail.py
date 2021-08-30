import base64
import mimetypes
import os
from pathlib import Path
from typing import Optional

from email.mime.audio import MIMEAudio
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from googleapiclient import errors


from . import LibraryContext, keyword


def get_size_format(b, factor=1024, suffix="B"):
    """
    Scale bytes to its proper byte format
    e.g:
        1253656 => '1.20MB'
        1253656678 => '1.17GB'
    """
    for unit in ["", "K", "M", "G", "T", "P", "E", "Z"]:
        if b < factor:
            return f"{b:.2f}{unit}{suffix}"
        b /= factor
    return f"{b:.2f}Y{suffix}"


def clean(text):
    # clean text for creating a folder
    return "".join(c if c.isalnum() else "_" for c in text)


class GmailKeywords(LibraryContext):
    """Class for Google Gmail API

    **Note:** The Gmail API does not work with _service accounts_

    For more information about Google Gmail API link_.

    .. _link: https://developers.google.com/gmail/api
    """

    def __init__(self, ctx):
        super().__init__(ctx)
        self.service = None

    @keyword(tags=["init", "gmail"])
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
        attachments: list = None,
    ):
        """Create a message for an email.

        :param to: message recipient
        :param subject: message subject
        :param message_text: message body text
        :param attachment: list of files to add as message attachments
        :return: An object containing a base64url encoded email object
        """
        mimeMessage = MIMEMultipart()
        mimeMessage["to"] = to
        mimeMessage["subject"] = subject
        mimeMessage.attach(MIMEText(message_text, "plain"))

        for at in attachments:
            self.add_attachment_to_message(mimeMessage, at)
        return {"raw": base64.urlsafe_b64encode(mimeMessage.as_bytes()).decode()}

    def add_attachment_to_message(self, mimeMessage, attachment):
        content_type, encoding = mimetypes.guess_type(attachment)

        if content_type is None or encoding is not None:
            content_type = "application/octet-stream"
        main_type, sub_type = content_type.split("/", 1)
        if main_type == "text":
            with open(attachment, "r") as fp:  # pylint: disable=unspecified-encoding
                msg = MIMEText(fp.read(), _subtype=sub_type)
        elif main_type == "image":
            with open(attachment, "rb") as fp:
                msg = MIMEImage(fp.read(), _subtype=sub_type)
        elif main_type == "audio":
            with open(attachment, "rb") as fp:
                msg = MIMEAudio(fp.read(), _subtype=sub_type)
        else:
            with open(attachment, "rb") as fp:
                msg = MIMEBase(main_type, sub_type)
                msg.set_payload(fp.read())
        filename = os.path.basename(attachment)
        msg.add_header("Content-Disposition", "attachment", filename=filename)
        mimeMessage.attach(msg)

    @keyword(tags=["gmail"])
    def send_message(
        self,
        sender: str,
        to: str,
        subject: str,
        message_text: str,
        attachments: list = None,
    ):
        """Send an email message.

        :param sender: message sender
        :param to: message recipient
        :param subject: message subject
        :param message_text: message body text
        :param attachment: list of files to add as message attachments
        :return: sent message

        Example:

        .. code-block:: robotframework

            ${attachments}=  Create List
            ...  ${CURDIR}${/}random.txt
            ...  ${CURDIR}${/}source.png
            Send Message    me
            ...    mika@robocorp.com
            ...    message subject
            ...    body of the message
            ...    ${attachments}
        """
        if not self.service:
            raise AssertionError("Gmail service has not been initialized")
        attachments = attachments or []
        message = self.create_message(to, subject, message_text, attachments)
        try:
            response = (
                self.service.users()
                .messages()
                .send(userId=sender, body=message)
                .execute()
            )
            self.logger.debug("Message Id: %s" % response["id"])
        except errors.HttpError as he:
            self.logger.warning(str(he))
            raise he
        return response

    def set_list_parameters(self, user_id, query, label_ids, max_results, include_spam):
        parameters = {"userId": user_id, "q": query}
        if label_ids:
            parameters["labelIds"] = ",".join(label_ids)
        if max_results:
            parameters["maxResults"] = max_results
        if include_spam:
            parameters["includeSpamTrash"] = include_spam
        return parameters

    def set_headers_to_message_dict(self, payload, message_id, response):
        headers = payload.get("headers")
        message_dict = {"id": message_id, "label_ids": response["labelIds"]}
        for header in headers:
            name = header.get("name")
            value = header.get("value")
            if name.lower() == "from":
                message_dict["from"] = value
            if name.lower() == "to":
                message_dict["to"] = value
            if name.lower() == "subject":
                message_dict["subject"] = value
            if name.lower() == "date":
                message_dict["date"] = value
        return message_dict

    def handle_mimetypes(self, parsed_parts, part, msg, folder_name):
        filename = part.get("filename")
        mimetype = part.get("mimeType")
        body = part.get("body")
        data = body.get("data")
        filesize = body.get("size")
        part_headers = part.get("headers")
        if mimetype == "text/plain":
            if data:
                text = base64.urlsafe_b64decode(data).decode()
                parsed_parts.append({"text/plain": text})
        elif mimetype == "text/html":
            if not filename:
                filename = "message.html"
            filepath = os.path.join(folder_name, filename)

            with open(filepath, "wb") as f:
                data = base64.urlsafe_b64decode(data)
                parsed_parts.append({"text/html": data, "path": filepath})
                f.write(data)
        else:
            for part_header in part_headers:
                part_header_name = part_header.get("name")
                part_header_value = part_header.get("value")
                if part_header_name == "Content-Disposition":
                    if "attachment" in part_header_value:
                        # we get the attachment ID
                        # and make another request to get the attachment itself
                        self.logger.info(
                            "Saving the file: %s, size:%s"
                            % (filename, get_size_format(filesize))
                        )
                        attachment_id = body.get("attachmentId")
                        attachment = (
                            self.service.users()
                            .messages()
                            .attachments()
                            .get(
                                id=attachment_id,
                                userId="me",
                                messageId=msg["id"],
                            )
                            .execute()
                        )
                        data = attachment.get("data")
                        filepath = os.path.join(folder_name, filename)
                        if data:
                            parsed_parts.append(
                                {"attachment": filepath, "id": attachment_id}
                            )
                            with open(filepath, "wb") as f:
                                f.write(base64.urlsafe_b64decode(data))

    @keyword(tags=["gmail"])
    def list_messages(
        self,
        user_id: str,
        query: str,
        folder_name: str = None,
        label_ids: list = None,
        max_results: int = None,
        include_json: bool = False,
        include_spam: bool = False,
    ):
        """List messages

        :param user_id: user's email address. The special value me can
         be used to indicate the authenticated user.
        :param query: message query
        :param folder_name: path where attachments are saved, default current
         directory
        :param label_ids: message label ids
        :param max_results: maximum number of message to return
        :param include_json: include original response json
        :param include_spam: include messages from SPAM and TRASH
        :return: messages

        Example:

        .. code-block:: robotframework

            ${messages}=    List Messages    me
            ...    from:mika@robocorp.com
            ...    folder_name=${CURDIR}${/}target
            ...    include_json=True
            FOR    ${msg}    IN    @{messages}
                Log Many    ${msg}
            END
        """
        parameters = self.set_list_parameters(
            user_id, query, label_ids, max_results, include_spam
        )
        folder_name = Path(folder_name) if folder_name else Path().absolute()
        messages = []
        try:
            response = self.service.users().messages().list(**parameters).execute()
            message_ids = [
                m["id"] for m in response["messages"] if "messages" in response.keys()
            ]
            for message_id in message_ids:
                response = (
                    self.service.users()
                    .messages()
                    .get(userId=user_id, id=message_id)
                    .execute()
                )
                payload = response["payload"]
                message_dict = self.set_headers_to_message_dict(
                    payload, message_id, response
                )
                if include_json:
                    message_dict["json"] = response
                parts = payload.get("parts")
                parsed_parts = self.parse_parts(
                    message_id, response, parts, folder_name
                )
                message_dict["parts"] = parsed_parts
                messages.append(message_dict)
        except errors.HttpError as he:
            self.logger.warning(str(he))
            raise he
        return messages

    def parse_parts(self, msg_id, msg, parts, folder_name):
        """
        Utility function that parses the content of an email partition
        """
        if msg_id and msg_id not in str(folder_name):
            try:
                folder_name = folder_name / msg_id
                folder_name.mkdir(parents=True, exist_ok=True)
            except FileExistsError:
                pass

        parsed_parts = []
        if parts:
            for part in parts:
                if part.get("parts"):
                    # recursively call this function when we see that a part
                    # has parts inside
                    self.parse_parts(None, msg, part.get("parts"), folder_name)
                self.handle_mimetypes(parsed_parts, part, msg, folder_name)

        return parsed_parts
