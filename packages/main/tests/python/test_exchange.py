import datetime
import functools

import mock
import pytest
from exchangelib.services import common as exchangelib_common
from exchangelib.util import post_ratelimited

from RPA.Email.Exchange import UTC, Exchange
from RPA.Robocorp.Vault import Vault

from . import RESOURCES_DIR


SENDMAIL_MOCK = "RPA.Email.Exchange.Message.send"
recipient = "person1@domain.com"
multi_recipients = "person2@domain.com,person3@domain.com"

# FIXME: Re-test and refactor every bad unit test. (explicitly skip the ones requiring
#  online Vault and valid credentials)
pytest.skip("until all tests are fixed", allow_module_level=True)


@pytest.fixture
def library():
    lib = Exchange()
    return lib


@pytest.fixture
def local_vault(monkeypatch):
    monkeypatch.setenv("RPA_SECRET_MANAGER", "RPA.Robocorp.Vault.FileSecrets")
    monkeypatch.setenv("RPA_SECRET_FILE", str(RESOURCES_DIR / "secrets.yaml"))
    return Vault()


def _extended_post_ratelimited(protocol, session, *args, **kwargs):
    session.post = functools.partial(
        session.post,
        client_id=protocol.credentials.client_id,
        client_secret=protocol.credentials.client_secret,
    )
    return post_ratelimited(protocol, session, *args, **kwargs)


@pytest.fixture(params=[True, False])
def is_oauth(monkeypatch, request):
    if request.param:  # OAuth2 flow enabled
        # Monkey-patching infinite loop fix on token refresh, due to OAuth2 library bug
        #  when passing the app credentials to the "/token" endpoint.
        monkeypatch.setattr(
            exchangelib_common, "post_ratelimited", _extended_post_ratelimited
        )
    return request.param


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
def test_send_message_with_multiple_recipients_as_list(mocked, library):
    multi_recipients_as_list = ["person2@domain.com, person3@domain.com"]
    status = library.send_message(recipients=multi_recipients_as_list)
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
def test_send_message_with_images(mocked, library):
    status = library.send_message(
        recipients=recipient, images=RESOURCES_DIR / "approved.png"
    )
    assert status


@mock.patch(SENDMAIL_MOCK)
def test_send_message_with_attachments(mocked, library):
    status = library.send_message(
        recipients=recipient, attachments=RESOURCES_DIR / "approved.png"
    )
    assert status


@mock.patch(SENDMAIL_MOCK)
def test_send_message_with_images_and_attachments(mocked, library):
    imagepath = str(RESOURCES_DIR / "approved.png")
    status = library.send_message(
        recipients=recipient, attachments=imagepath, images=imagepath
    )
    assert status


def test_get_filter_key_value_unknown_criterion_key(library):
    with pytest.raises(KeyError):
        _ = library._get_filter_key_value("dfddff")
    with pytest.raises(KeyError):
        _ = library._get_filter_key_value("dfddff:a")
    with pytest.raises(KeyError):
        _ = library._get_filter_key_value("dfddff:")


def test_get_filter_key_value_dates(library):
    default_start = datetime.datetime(1972, 1, 1, tzinfo=UTC)
    default_end = datetime.datetime(2050, 1, 1, tzinfo=UTC)
    date_1 = library._parse_date_from_string("05-05-2020")
    date_2 = library._parse_date_from_string("01-02-2021")

    criterias = {
        "before:01-02-2021": {
            "datetime_received__range": (default_start, date_2),
        },
        "after:05-05-2020": {
            "datetime_received__range": (date_1, default_end),
        },
        "between:'05-05-2020 and 01-02-2021'": {
            "datetime_received__range": (date_1, date_2),
        },
    }

    for criteria, expected in criterias.items():
        result = library._get_filter_key_value(criteria)
        assert result == expected


def test_get_filter_key_value_by_importance(library):
    result = library._get_filter_key_value("importance:high")
    assert result == {"importance": "High"}


def test_get_filter_key_value_by_category(library):
    result = library._get_filter_key_value("category:green")
    assert result == {"categories": "green"}


def test_get_filter_key_value_by_category_contains(library):
    result = library._get_filter_key_value("category_contains:green")
    assert result == {"categories__contains": "green"}


def test_get_filter_key_value_by_body(library):
    result = library._get_filter_key_value("body:'Content in the email body'")
    assert result == {"body": "Content in the email body"}


def test_get_filter_key_value_by_body_contains(library):
    result = library._get_filter_key_value("body_contains:'email body'")
    assert result == {"body__contains": "email body"}


def test_get_filter_key_value_by_subject(library):
    result = library._get_filter_key_value("subject:'Hello World'")
    assert result == {"subject": "Hello World"}


def test_get_filter_key_value_by_subject_contains(library):
    result = library._get_filter_key_value("subject_contains:buy")
    assert result == {"subject__contains": "buy"}


def test_get_filter_key_value_by_sender(library):
    result = library._get_filter_key_value("sender:name@domain.com")
    assert result == {"sender": "name@domain.com"}


def test_get_filter_key_value_by_sender_contains(library):
    result = library._get_filter_key_value("sender_contains:name@domain.com")
    assert result == {"sender__contains": "name@domain.com"}


def test_get_filter_by_key_value_multiple_conditions(library):
    criterias = {
        "sender:robocorp.tester@gmail.com and subject:epic": {
            "sender": "robocorp.tester@gmail.com",
            "subject": "epic",
        },
        "sender_contains:robocorp.tester@gmail.com and subject:'epic level'": {
            "sender__contains": "robocorp.tester@gmail.com",
            "subject": "epic level",
        },
        # first quoted criteria is prioritized
        "body_contains:message and body_contains:'epic level'": {
            "body__contains": "epic level",
        },
        # first quoted criteria is prioritized
        "body_contains:'message' and body_contains:'epic level'": {
            "body__contains": "message",
        },
    }

    for criteria, expected in criterias.items():
        result = library._get_filter_key_value(criteria)
        assert result == expected


@pytest.mark.skip(reason="requires online Vault and valid e-mail account")
@pytest.mark.parametrize("to_self", [True, False])
def test_send_message_with_out_bcc_addresses(library, local_vault, is_oauth, to_self):
    secrets = local_vault.get_secret("exchange")
    if is_oauth:
        params = {
            "access_type": "IMPERSONATE",
            "client_id": secrets["client_id"],
            "client_secret": secrets["client_secret"],
            "token": secrets["token"],
        }
    else:
        params = {
            "password": secrets["password"],
        }
    library.authorize(
        username=secrets["account"],
        autodiscover=False,
        server="outlook.office365.com",
        is_oauth=is_oauth,
        **params,
    )
    if to_self:
        recipient = secrets["account"]
        bcc_list = []
        body = "Sent to self without BCC"
    else:
        recipient = None
        bcc_list = ["robocorp.tester@gmail.com", "robocorp.tester.2@gmail.com"]
        body = "Sent to others with BCC only"
    library.send_message(
        recipients=recipient,
        bcc=bcc_list,
        subject="test_send_message_with_out_bcc_addresses",
        body=f"{body} ({'OAuth2' if is_oauth else 'basic'})",
    )
