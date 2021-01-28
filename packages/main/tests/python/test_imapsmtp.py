import pytest
import mock
from pathlib import Path
from RPA.Email.ImapSmtp import ImapSmtp
from smtplib import SMTP

RESOURCE_DIR = Path(__file__).resolve().parent / ".." / "resources"
SENDMAIL_MOCK = "RPA.Email.ImapSmtp.SMTP.sendmail"
recipient = "person1@domain.com"
multi_recipients = "person2@domain.com,person3@domain.com"


@pytest.fixture
def library():
    library = ImapSmtp()
    library.smtp_conn = SMTP()
    return library


@mock.patch(SENDMAIL_MOCK)
def test_send_message_all_required_parameters_given(mocked, library):
    status = library.send_message(
        sender="sender@domain.com",
        subject="My test email subject",
        body="body of the message",
        recipients=recipient,
    )
    assert status


@mock.patch(SENDMAIL_MOCK)
def test_send_message_with_no_sender(mocked, library):
    with pytest.raises(TypeError):
        library.send_message(
            subject="My test email subject",
            body="body of the message",
            recipients=recipient,
        )


@mock.patch(SENDMAIL_MOCK)
def test_send_message_with_no_recipients(mocked, library):
    with pytest.raises(TypeError):
        library.send_message(
            sender="sender@domain.com",
            subject="My test email subject",
            body="body of the message",
        )


@mock.patch(SENDMAIL_MOCK)
def test_send_message_with_images(mocked, library):
    status = library.send_message(
        sender="sender@domain.com",
        subject="My test email subject",
        body="body of the message<img src='approved.png'/>",
        recipients=recipient,
        html=True,
        images=RESOURCE_DIR / "approved.png",
    )
    assert status


@mock.patch(SENDMAIL_MOCK)
def test_send_message_with_attachments(mocked, library):
    status = library.send_message(
        sender="sender@domain.com",
        subject="My test email subject",
        body="body of the message",
        recipients=recipient,
        attachments=RESOURCE_DIR / "approved.png",
    )
    assert status


@mock.patch(SENDMAIL_MOCK)
def test_send_message_with_attachments_and_images(mocked, library):
    status = library.send_message(
        sender="sender@domain.com",
        subject="My test email subject",
        body="body of the message",
        recipients=recipient,
        attachments=RESOURCE_DIR / "approved.png",
        html=True,
        images=RESOURCE_DIR / "approved.png",
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
