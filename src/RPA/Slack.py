import json
import logging
import requests


class Slack:
    """RPA Framework library for Slack operations.

    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def slack_message_using_webhook(
        self, webhook_url, channel, sender, text, icon_emoji=None
    ):
        """Send message to Slack channel using webhook.

        :param webhook_url: needs to be configured for the Slack server
        :param channel: channel needs to exist in the Slack server
        :param sender: shown in the message post as sender
        :param text: text for the message post
        :param icon_emoji: icon for the message post, defaults to None
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
        self.logger.debug(f"{response.status_code}")
