########
Notifier
########

.. contents:: Table of Contents
   :local:
   :depth: 1

***********
Description
***********

`Notifier` is a library interfacting with different notification services.

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


********
Examples
********

Robot Framework
===============

.. code-block:: robotframework
   :linenos:

   *** Settings ***
   Library  RPA.Notifier

   *** Variables ***
   ${SLACK_WEBHOOK}   https://hooks.slack.com/services/WEBHOOKDETAILS
   ${CHANNEL}         notification-channel

   *** Tasks ***
   Lets notify
      Notify Slack   message from robot  channel=${CHANNEL}  webhook_url=${SLACK_WEBHOOK}

Python
======

.. code-block:: python
   :linenos:

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

*****************
API Documentation
*****************

.. toctree::
   :maxdepth: 1

   ../../libdoc/Notifier.rst
   python
