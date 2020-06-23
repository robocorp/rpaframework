import pytest
import mock
from pathlib import Path
from RPA.Email.Exchange import Exchange

RESOURCE_DIR = Path(__file__).resolve().parent / ".." / "resources"
SENDMAIL_MOCK = "RPA.Email.Exchange.Message.send"
recipient = "person1@domain.com"
multi_recipients = "person2@domain.com,person3@domain.com"


@pytest.fixture
def library():
    return Exchange()


@mock.patch(SENDMAIL_MOCK)
def test_send_message_no_recipients_raises(mocked, library):
    with pytest.raises(TypeError):
        library.send_message(subject="My test email subject")


@mock.patch(SENDMAIL_MOCK)
def test_send_message_with_recipients(mocked, library):
    status = library.send_message(recipients=recipient)
    assert status


@mock.patch(SENDMAIL_MOCK)
def test_send_message_with_multiple_recipients(mocked, library):
    status = library.send_message(recipients=multi_recipients)
    assert status


@mock.patch(SENDMAIL_MOCK)
def test_send_with_subject(mocked, library):
    status = library.send_message(recipients=recipient, subject="My test email subject")
    assert status


@mock.patch(SENDMAIL_MOCK)
def test_send_with_body(mocked, library):
    status = library.send_message(
        recipients=recipient, body="email body of the message"
    )
    assert status


@mock.patch(SENDMAIL_MOCK)
def test_send_with_html_body_but_in_plaintext(mocked, library):
    status = library.send_message(
        recipients=recipient, body="<p>email <b>body</b> of the message</p>"
    )
    assert status


@mock.patch(SENDMAIL_MOCK)
def test_send_with_html_body_html_format(mocked, library):
    status = library.send_message(
        recipients=recipient, body="<p>email <b>body</b> of the message</p>", html=True
    )
    assert status


@mock.patch(SENDMAIL_MOCK)
def test_send_with_html_body_html_format(mocked, library):
    status = library.send_message(
        recipients=recipient, body="<p>email <b>body</b> of the message</p>", html=True
    )
    assert status


@mock.patch(SENDMAIL_MOCK)
def test_send_message_with_images(mocked, library):
    status = library.send_message(
        recipients=recipient, images=RESOURCE_DIR / "approved.png"
    )
    assert status


@mock.patch(SENDMAIL_MOCK)
def test_send_message_with_attachments(mocked, library):
    status = library.send_message(
        recipients=recipient, attachments=RESOURCE_DIR / "approved.png"
    )
    assert status


@mock.patch(SENDMAIL_MOCK)
def test_send_message_with_images_and_attachments(mocked, library):
    imagepath = str(RESOURCE_DIR / "approved.png")
    status = library.send_message(
        recipients=recipient, attachments=imagepath, images=imagepath
    )
    assert status
