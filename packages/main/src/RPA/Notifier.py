import logging
from notifiers import notify


class Notifier:
    """`Notifier` is a library interfacting with different notification services.

    Supported services:

    - email
    - gmail
    - pushover
    - slack
    - telegram
    - twilio

    Services not supported yet:

    - gitter
    - join
    - mailgun
    - pagerduty
    - popcornnotify
    - pushbullet
    - simplepush
    - statuspage
    - zulip

    Read more at https://notifiers.readthedocs.io/en/latest/

    **Examples**

    **Robot Framework**

    .. code-block:: robotframework

       *** Settings ***
       Library  RPA.Notifier

       *** Variables ***
       ${SLACK_WEBHOOK}   https://hooks.slack.com/services/WEBHOOKDETAILS
       ${CHANNEL}         notification-channel

       *** Tasks ***
       Lets notify
          Notify Slack   message from robot  channel=${CHANNEL}  webhook_url=${SLACK_WEBHOOK}

    **Python**

    .. code-block:: python

       from RPA.Notifier import Notifier

       library = Notifier()

       slack_attachments = [
          {
             "title": "attachment 1",
             "fallback": "liverpool logo",
             "image_url": "https://upload.wikimedia.org/wikipedia/fi/thumb/c/cd/Liverpool_FC-n_logo.svg/1200px-Liverpool_FC-n_logo.svg.png",
          }
       ]

       library.notify_slack(
          message='message for the Slack',
          channel="notification-channel",
          webhook_url=slack_webhook_url,
          attachments=slack_attachments,
       )
    """  # noqa: E501

    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    ROBOT_LIBRARY_DOC_FORMAT = "REST"

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def notify_pushover(
        self, message: str = None, user: str = None, token: str = None, **kwargs: dict
    ) -> bool:
        """Notify using Pushover service

        :param message: notification message
        :param user: target user for the notification
        :param token: service token
        :return: True is notification was success, False if not
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
        """Notify using Slack service

        :param message: notification message
        :param channel: target channel for the notification
        :param webhook_url: Slack webhook url
        :return: True is notification was success, False if not
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

        :param message: notification message
        :param chat_id: target chat id for the notification
        :param token: service token
        :return: True is notification was success, False if not
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
        """Notify using Gmail service

        :param message: notification message
        :param to: target of email message
        :param username: GMail service username
        :param password: GMail service password
        :return: True is notification was success, False if not
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
        """Notify using email service

        :param message: notification message
        :param to: target of email message
        :param username: email service username
        :param password: email service password
        :return: True is notification was success, False if not
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
        """Notify using Twilio service

        :param message: notification message
        :param number_from: number where the message comes from
        :param number_to: number where the messages goes to
        :param account_sid: Twilio account SID
        :param token: Twilio account token
        :return: True is notification was success, False if not
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
