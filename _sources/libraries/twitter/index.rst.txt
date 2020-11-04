#######
Twitter
#######

.. contents:: Table of Contents
   :local:
   :depth: 1

***********
Description
***********

`Twitter` is a library for accessing Twitter using developer API.
The library extends `tweepy`_ library.

Authorization credentials can be given as parameters for ``authorize`` keyword
or keyword can read them in as environment variables:

- `TWITTER_CONSUMER_KEY`
- `TWITTER_CONSUMER_SECRET`
- `TWITTER_ACCESS_TOKEN`
- `TWITTER_ACCESS_TOKEN_SECRET`

Library usage requires Twitter developer credentials. Those can be requested from `Twitter developer site`_

.. _tweepy:
    http://docs.tweepy.org/en/latest/index.html

.. _Twitter developer site:
    https://developer.twitter.com/

********
Examples
********

Robot Framework
===============

.. code-block:: robotframework
    :linenos:

    *** Settings ***
    Library   RPA.Twitter

    *** Tasks ***
    Get user tweets and like them
        [Setup]   Authorize
        @{tweets}=   Get User Tweets   username=niinisto   count=5
        FOR   ${tweet}  IN   @{tweets}
            Like   ${tweet}
        END

Python
======

.. code-block:: python
    :linenos:

    from RPA.Twitter import Twitter

    library = Twitter()
    library.authorize()
    tweets = library.get_user_tweets(username="niinisto", count=5)
    for tw in tweets:
        library.like(tw)
    tweets = library.text_search_tweets(query="corona trump")
    for tw in tweets:
        print(tw.text)
    user = library.get_user_profile("niinisto")
    library.follow(user)
    library.tweet("first tweet")
    me = library.get_me()
    print(me)


*****************
API Documentation
*****************

See :download:`libdoc documentation <../../libdoc/RPA_Twitter.html>`.

.. toctree::
   :maxdepth: 1

   ../../robot/Twitter.rst
   python
