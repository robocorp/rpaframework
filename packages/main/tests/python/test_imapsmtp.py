from email import message_from_bytes
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from types import SimpleNamespace
from unittest import mock

import pytest
from RPA.Email.ImapSmtp import ImapSmtp
from RPA.Email.common import counter_duplicate_path
from docx import Document

from . import RESOURCES_DIR


class Resources:
    image = RESOURCES_DIR / "approved.png"
    email = RESOURCES_DIR / "emails" / "work-item-documentation.eml"


@pytest.fixture
def library():
    with mock.patch("RPA.Email.ImapSmtp.SMTP"), mock.patch(
        "RPA.Email.ImapSmtp.IMAP4_SSL"
    ):
        lib = ImapSmtp(smtp_server="smtp.gmail.com", imap_server="imap.gmail.com")
        yield lib


@pytest.fixture
def creds():
    return SimpleNamespace(
        account="cosmin@robocorp.com",
        password="robocorp-is-cool",
        oauth2_str=(
            "dXNlcj14b2F1dGhAZ21haWwuY29tAWF1dGg9QmVhcmVyIHlhMjkuQUhFUzZaUktlVVF3SDJ4aG"
            "lya3NTVURTeWpnOW9QdVJNTWFsMDVUeTBjZkZJVF91UmZFU0h3AQE="
        ),
    )


@pytest.fixture(
    params=[
        "person1@domain.com",
        "person2@domain.com,person3@domain.com",
    ]
)
def recipients(request):
    return request.param


# TODO(mikahanninen): Implement proper way of handling @smtp_connection decorator
# for send_message
def test_send_message_all_required_parameters_given(library, recipients):
    with pytest.raises(ValueError):
        status = library.send_message(
            sender="sender@domain.com",
            subject="My test email subject",
            body="body of the message",
            recipients=recipients,
        )
        assert status


def test_send_message_with_no_sender(library, recipients):
    with pytest.raises(ValueError):
        library.send_message(
            subject="My test email subject",
            body="body of the message",
            recipients=recipients,
        )


def test_send_message_with_no_recipients(library):
    with pytest.raises(ValueError):
        library.send_message(
            sender="sender@domain.com",
            subject="My test email subject",
            body="body of the message",
        )


def test_send_message_with_images(library, recipients):
    with pytest.raises(ValueError):
        status = library.send_message(
            sender="sender@domain.com",
            subject="My test email subject",
            body="body of the message<img src='approved.png'/>",
            recipients=recipients,
            html=True,
            images=Resources.image,
        )
        assert status


def test_send_message_with_attachments(library, recipients):
    with pytest.raises(ValueError):
        status = library.send_message(
            sender="sender@domain.com",
            subject="My test email subject",
            body="body of the message",
            recipients=recipients,
            attachments=Resources.image,
        )
        assert status


def test_send_message_with_attachments_and_images(library, recipients):
    with pytest.raises(ValueError):
        status = library.send_message(
            sender="sender@domain.com",
            subject="My test email subject",
            body="body of the message",
            recipients=recipients,
            attachments=Resources.image,
            html=True,
            images=Resources.image,
        )
        assert status


def test_parse_folders_gmail(library):
    folders = [
        b'(\\HasNoChildren) "/" "INBOX"',
        b'(\\HasChildren \\Noselect) "/" "[Gmail]"',
        b'(\\All \\HasNoChildren) "/" "[Gmail]/All Mail"',
    ]

    expected = [
        {"delimiter": "/", "flags": "\\HasNoChildren", "name": "INBOX"},
        {"delimiter": "/", "flags": "\\HasChildren \\Noselect", "name": "[Gmail]"},
        {
            "delimiter": "/",
            "flags": "\\All \\HasNoChildren",
            "name": "[Gmail]/All Mail",
        },
    ]

    result = library._parse_folders(folders)

    assert result == expected


def test_parse_folders_outlook(library):
    folders = [
        b'(\\HasNoChildren) "/" Archive',
        b'(\\HasNoChildren \\Trash) "/" Deleted',
        b'(\\HasNoChildren \\Drafts) "/" Drafts',
    ]
    expected = [
        {"delimiter": "/", "flags": "\\HasNoChildren", "name": "Archive"},
        {"delimiter": "/", "flags": "\\HasNoChildren \\Trash", "name": "Deleted"},
        {"delimiter": "/", "flags": "\\HasNoChildren \\Drafts", "name": "Drafts"},
    ]
    result = library._parse_folders(folders)

    assert result == expected


def test_parse_folders_failed(library, caplog):
    folders = [b"Totally invalid folder_name"]
    expected_log_text = "Cannot parse folder name Totally invalid folder_name"
    result = library._parse_folders(folders)

    assert not result
    assert expected_log_text in caplog.text


def test_email_to_document(tmp_path, library):
    output_source = tmp_path / f"{Resources.email.stem}.docx"
    library.email_to_document(Resources.email, output_source)

    doc = Document(output_source)
    texts = [para.text for para in doc.paragraphs]
    expected_text = (
        "Get attached file from work item to disk. Returns the absolute path to the "
        "created file."
    )
    assert expected_text in texts


def test_basic_authorization(library, creds):
    library.authorize(account=creds.account, password=creds.password)
    library.imap_conn.login.assert_called_once_with(creds.account, creds.password)
    library.smtp_conn.login.assert_called_once_with(creds.account, creds.password)


def test_oauth_authorization(library, creds):
    library.authorize(account=creds.account, password=creds.oauth2_str, is_oauth=True)

    authenticate_call = library.imap_conn.authenticate.call_args[0]
    assert authenticate_call[0] == "XOAUTH2"
    assert b"xoauth@gmail.com" in authenticate_call[1](None)

    auth_call = library.smtp_conn.auth.call_args[0]
    assert auth_call[0] == "XOAUTH2"
    assert "xoauth@gmail.com" in auth_call[1]()


def test_counter_duplicate_path(tmp_path):
    file_path = tmp_path / "my-attachment.txt"
    new_file_path = counter_duplicate_path(file_path)
    assert new_file_path == file_path

    file_path.write_text("some data")
    new_file_path = counter_duplicate_path(file_path)
    assert new_file_path != file_path
    assert new_file_path.name == "my-attachment-2.txt"

    new_file_path.write_text("some data 2")
    newest_file_path = counter_duplicate_path(file_path)
    assert newest_file_path.name == "my-attachment-3.txt"


def _multipart_message(*parts):
    message = MIMEMultipart()
    for part in parts:
        message.attach(part)
    return message_from_bytes(message.as_bytes())


def _part_without_charset(maintype, subtype, payload):
    part = MIMEBase(maintype, subtype)
    part.set_payload(payload)
    assert part.get_content_charset() is None
    return part


def test_get_decoded_email_body_text_without_charset(library):
    message = _multipart_message(_part_without_charset("text", "plain", "invoice body"))

    body, has_attachments = library.get_decoded_email_body(message)

    assert body == "invoice body"
    assert not has_attachments


def test_get_decoded_email_body_html_without_charset(library):
    message = _multipart_message(
        MIMEText("plain body", "plain", "utf-8"),
        _part_without_charset("text", "html", "<p>html body</p>"),
    )

    assert library.get_decoded_email_body(message)[0] == "plain body"
    assert library.get_decoded_email_body(message, html_first=True)[0] == (
        "<p>html body</p>"
    )


def test_get_decoded_email_body_ignores_inline_binary(library):
    message = _multipart_message(
        MIMEText("plain body", "plain", "utf-8"),
        _part_without_charset("image", "png", "not really an image"),
    )

    body, has_attachments = library.get_decoded_email_body(message)

    assert body == "plain body"
    assert not has_attachments
