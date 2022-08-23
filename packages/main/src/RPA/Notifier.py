import logging
from notifiers import notify


class Notifier:
    """`Notifier` is a library interfacting with different notification providers.

    **Supported providers**

    - email
    - gmail
    - pushover
    - slack
    - telegram
    - twilio

    **Providers not supported yet via specific keywords**

    - gitter
    - join
    - mailgun
    - pagerduty
    - popcornnotify
    - pushbullet
    - simplepush
    - statuspage
    - zulip

    There is a keyword ``Generic Notify`` which can be used
    to call above services, for example.

    .. code-block:: robotframework

        Generic Notify
            provider_name=gitter
            message=Hello from Robot
            token=TOKEN
            room_id=ID_OF_THE_GITTER_ROOM

    Parameters for different providers can be read from the
    **Notifiers** documents (link below).

    Read more at https://notifiers.readthedocs.io/en/latest/


    **About kwargs**

    The `**kwargs` is a term for any extra named parameters, which
    can be included in the same way as already named arguments,
    e.g. ``Notify Email`` could be called with `subject=my email subject`
    which will be passed through `**kwargs`.

    Notifier documentation contains information about all possible
    arguments that different providers support.

    **Robot Framework**

    .. code-block:: robotframework

        &{account}=    Create Dictionary
        ...    host=smtp.office365.com
        ...    username=ACCOUNT_USERNAME
        ...    password=ACCOUNT_PASSWORD
        Notify Email
        ...    to=RECIPIENT_EMAIL
        ...    from_=SENDER_ADDRESS            # passed via kwargs
        ...    subject=Hello from the Robot    # passed via kwargs
        ...    message=Hello from the Robot
        ...    &{account}                      # passed via kwargs

    .. code-block:: python

        notifier = Notifier()
        account = {
            "host": "smtp.office365.com",
            "username": "EMAIL_USERNAME",
            "password": "EMAIL_PASSWORD"
        }
        notifier.email_notify(
            to="RECIPIENT_EMAIL",
            from_="SENDER_EMAIL",
            subject="Hello from the Python Robot",
            message="Hello from the Python RObot",
            **account
        )

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
        self, message: str = None, user: str = None, token: str = None, **kwargs
    ) -> bool:
        """Notify using Pushover provider

        :param message: notification message
        :param user: target user for the notification
        :param token: service token
        :param kwargs: see library documentation
        :return: True if notification was successful, False if not
        """
        arguments = {
            "provider_name": "pushover",
            "message": message,
            "user": user,
            "token": token,
        }
        notify_arguments = {**arguments, **kwargs}
        response = notify(**notify_arguments)
        return self._handle_response(response)

    def notify_slack(
        self,
        message: str = None,
        channel: str = None,
        webhook_url: str = None,
        **kwargs,
    ) -> bool:
        """Notify using Slack provider

        :param message: notification message
        :param channel: target channel for the notification
        :param webhook_url: Slack webhook url
        :param kwargs: see library documentation
        :return: True if notification was successful, False if not
        """
        arguments = {
            "provider_name": "slack",
            "message": message,
            "webhook_url": webhook_url,
            "channel": channel,
        }
        notify_arguments = {**arguments, **kwargs}
        response = notify(**notify_arguments)
        return self._handle_response(response)

    def notify_telegram(
        self,
        message: str = None,
        chat_id: str = None,
        token: str = None,
        **kwargs,
    ) -> bool:
        """Notify using Telegram provider

        :param message: notification message
        :param chat_id: target chat id for the notification
        :param token: service token
        :param kwargs: see library documentation
        :return: True if notification was successful, False if not
        """
        arguments = {
            "provider_name": "telegram",
            "message": message,
            "chat_id": chat_id,
            "token": token,
        }
        notify_arguments = {**arguments, **kwargs}
        response = notify(**notify_arguments)
        return self._handle_response(response)

    def notify_gmail(
        self,
        message: str = None,
        to: str = None,
        username: str = None,
        password: str = None,
        **kwargs,
    ) -> bool:
        """Notify using Gmail provider

        :param message: notification message
        :param to: target of email message
        :param username: GMail account username
        :param password: GMail account password
        :param kwargs: see library documentation
        :return: True if notification was successful, False if not
        """
        arguments = {
            "provider_name": "gmail",
            "message": message,
            "to": to,
            "username": username,
            "password": password,
        }
        notify_arguments = {**arguments, **kwargs}
        response = notify(**notify_arguments)
        return self._handle_response(response)

    def notify_email(
        self,
        message: str = None,
        to: str = None,
        username: str = None,
        password: str = None,
        host: str = None,
        port: int = 587,
        tls: bool = True,
        **kwargs,
    ) -> bool:
        """Notify using email provider

        :param message: notification message
        :param to: target of email message
        :param username: email account username
        :param password: email account password
        :param host: email SMTP host name
        :param port: email SMTP host port number
        :param tls: should TLS be used (default True)
        :param kwargs: see library documentation
        :return: True if notification was successful, False if not

        Example.

        .. code:: robotframework

            # Notify with Outlook account
            Notify Email
            ...   message=Message from the Robot
            ...   to=RECIPIENT_EMAIL_ADDRESS
            ...   username=OUTLOOK_USERNAME
            ...   password=OUTLOOK_PASSWORD
            ...   host=smtp.office365.com
            ...   subject=Subject of the Message
        """
        arguments = {
            "provider_name": "email",
            "message": message,
            "to": to,
            "username": username,
            "password": password,
            "host": host,
            "port": port,
            "tls": tls,
        }
        notify_arguments = {**arguments, **kwargs}
        response = notify(**notify_arguments)
        return self._handle_response(response)

    def notify_twilio(
        self,
        message: str = None,
        number_from: str = None,
        number_to: str = None,
        account_sid: str = None,
        token: str = None,
        **kwargs,
    ) -> bool:
        """Notify using Twilio provider

        :param message: notification message
        :param number_from: number where the message comes from
        :param number_to: number where the messages goes to
        :param account_sid: Twilio account SID
        :param token: Twilio account token
        :param kwargs: see library documentation
        :return: True if notification was successful, False if not
        """
        arguments = {
            "provider_name": "twilio",
            "message": message,
            "from_": number_from,
            "to": number_to,
            "account_sid": account_sid,
            "auth_token": token,
        }
        notify_arguments = {**arguments, **kwargs}
        response = notify(**notify_arguments)
        return self._handle_response(response)

    def generic_notify(self, provider_name: str, **kwargs):
        """Generic keyword to use with any notifier provider.

        :param provider_name: name of the notifier service
        :param kwargs: see library documentation
        :return: True if notification was successful, False if not
        """
        notify_arguments = {"provider_name": provider_name, **kwargs}
        response = notify(**notify_arguments)
        return self._handle_response(response)

    def _handle_response(self, response) -> bool:
        if response.status == "Success":
            self.logger.info("Notify %s resulted in Success", response.provider)
            return True
        else:
            self.logger.error("Notify errors: %s", response.errors)
            return False
