import logging
from notifiers import notify


class Notifier:
    """
    Library for using different notification services.

    All keywords take keyword arguments (**kwargs) to allow giving
    additional arguments for the notifications.
    """

    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    ROBOT_LIBRARY_DOC_FORMAT = "ROBOT"

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def notify_pushover(
        self, message: str = None, user: str = None, token: str = None, **kwargs: dict
    ) -> bool:
        """Notify using Pushover service.

        Send a ``message`` to a given ``user``. Service ``token`` is given for authentication.

        Returns a boolean value indicating if notification was sent.
        """
        response = notify("pushover", message=message, user=user, token=token, **kwargs)
        return self._handle_response(response)

    def notify_slack(
        self,
        message: str = None,
        channel: str = None,
        webhook_url: str = None,
        **kwargs: dict,
    ) -> bool:
        """Notify using Slack service.

        Send a ``message`` to a given ``channel``.
        A ``webhook_url`` to the Slack instance should be supplied.

        Returns a boolean value indicating if notification was sent.
        """
        response = notify(
            "slack",
            message=message,
            webhook_url=webhook_url,
            channel=channel,
            **kwargs,
        )
        return self._handle_response(response)

    def notify_telegram(
        self,
        message: str = None,
        chat_id: str = None,
        token: str = None,
        **kwargs: dict,
    ) -> bool:
        """Notify using Telegram service

        Send a ``message`` to a given target ``chat_id``.
        Service ``token`` is given for authentication.

        Returns a boolean value indicating if notification was sent.
        """
        response = notify(
            "telegram", message=message, chat_id=chat_id, token=token, **kwargs
        )
        return self._handle_response(response)

    def notify_gmail(
        self,
        message: str = None,
        to: str = None,
        username: str = None,
        password: str = None,
        **kwargs: dict,
    ) -> bool:
        """Notify using Gmail service.

        Send an email ``message`` to a given ``to`` recipient.
        A GMail service ``username`` and ``password`` should be supplied.

        Returns a boolean value indicating if notification was sent.
        """
        response = notify(
            "gmail",
            message=message,
            to=to,
            username=username,
            password=password,
            **kwargs,
        )
        return self._handle_response(response)

    def notify_email(
        self,
        message: str = None,
        to: str = None,
        username: str = None,
        password: str = None,
        **kwargs: dict,
    ) -> bool:
        """Notify using email service.

        Send an email ``message`` to a given ``to`` recipient.
        An email service ``username`` and ``password`` should be supplied.

        Returns a boolean value indicating if notification was sent.
        """
        response = notify(
            "email",
            message=message,
            to=to,
            username=username,
            password=password,
            **kwargs,
        )
        return self._handle_response(response)

    def notify_twilio(
        self,
        message: str = None,
        number_from: str = None,
        number_to: str = None,
        account_sid: str = None,
        token: str = None,
        **kwargs: dict,
    ) -> bool:
        """Notify using Twilio service.

        Send a notification ``message`` between two numbers
        indicated with ``number_from`` and ``number_to``.

        A Twili account SID and token should be supplied through ``account_sid``
        and ``token`` arguments.

        Returns a boolean value indicating if notification was sent.
        """
        response = notify(
            "twilio",
            message=message,
            from_=number_from,
            to=number_to,
            account_sid=account_sid,
            auth_token=token,
            **kwargs,
        )
        return self._handle_response(response)

    def _handle_response(self, response):
        if response.status == "Success":
            self.logger.info("Notify %s resulted in Success", response.provider)
            return True
        else:
            self.logger.error("Notify errors: %s", response.errors)
            return False
