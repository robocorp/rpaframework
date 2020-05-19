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
