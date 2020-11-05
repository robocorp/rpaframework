import json
import logging
import requests


class Slack:
    """RPA Framework library for Slack operations."""

    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    ROBOT_LIBRARY_DOC_FORMAT = "ROBOT"

    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)

    def slack_message_using_webhook(
        self,
        webhook_url: str,
        channel: str,
        sender: str,
        text: str,
        icon_emoji: str = None,
    ):
        """Send message to Slack channel using webhook.

        The destination ``webhook_url`` is configured for the Slack server.

        Optionally an emoji can be shown as the icon for the post,
        given with the ``icon_emoji`` option.
        """
        headers = {"Content-Type": "application/json"}
        payload = {
            "channel": channel if "#" in channel else f"#{channel}",
            "username": sender,
            "text": text,
        }
        if icon_emoji:
            payload["icon_emoji"] = icon_emoji
        response = requests.post(webhook_url, headers=headers, data=json.dumps(payload))
        self.logger.debug(response.status_code)
