from dataclasses import dataclass
import datetime
import logging
from robot.libraries.BuiltIn import (
    BuiltIn,
    RobotNotRunningError,
)
import tweepy
from tweepy.error import TweepError

from RPA.core.helpers import required_env, required_param
from RPA.core.notebook import notebook_json
from RPA.RobotLogListener import RobotLogListener


try:
    BuiltIn().import_library("RPA.RobotLogListener")
except RobotNotRunningError:
    pass


@dataclass
class Tweet:
    """Container for single Tweet."""

    created_at: datetime.datetime
    id: int
    tweet_id_str: str
    text: str
    in_reply_to_screen_name: str
    lang: str
    name: str
    screen_name: str
    hashtags: list
    is_truncated: bool = False
    favorite_count: int = 0
    retweeted: bool = False
    retweet_count: int = 0


class Twitter:
    """Library for interacting with Twitter.

    Usage requires Twitter developer credentials, which can
    be requested from https://developer.twitter.com/.
    """

    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    ROBOT_LIBRARY_DOC_FORMAT = "ROBOT"

    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)
        self.api = None
        self._auth = None
        self._me = None
        listener = RobotLogListener()
        listener.register_protected_keywords("authorize")
        listener.only_info_level(
            [
                "get_me",
                "get_user_tweets",
                "text_search_tweets",
                "get_user_profile",
                "tweet",
                "like",
                "unlike",
            ]
        )

    def authorize(
        self,
        consumer_key: str = None,
        consumer_secret: str = None,
        access_token: str = None,
        access_token_secret: str = None,
    ) -> None:
        """Authorize to Twitter API.

        ``consumer_key`` and ``consumer_secret`` are the app consumer key and secret

        ``access_token`` and ``access_token_secret`` are the user access token and secret
        """
        if consumer_key is None:
            consumer_key = required_env("TWITTER_CONSUMER_KEY")
        if consumer_secret is None:
            consumer_secret = required_env("TWITTER_CONSUMER_SECRET")
        if access_token is None:
            access_token = required_env("TWITTER_ACCESS_TOKEN")
        if access_token_secret is None:
            access_token_secret = required_env("TWITTER_ACCESS_TOKEN_SECRET")
        self._auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
        self._auth.set_access_token(access_token, access_token_secret)
        self.api = tweepy.API(self._auth, wait_on_rate_limit=True)
        try:
            self.api.verify_credentials()
            self.logger.info("Twitter authentication success")
            self._me = self.api.me()
        except TweepError as e:
            self.logger.error("Error during Twitter authentication: %s", str(e))
            raise TweepError from e

    def get_me(self) -> dict:
        """Get Twitter profile of authenticated user."""
        data = self._me._json if self._me else None  # pylint: disable=W0212
        notebook_json(data)
        return data

    def get_user_tweets(self, username: str = None, count: int = 100) -> list:
        """Get tweets from user with given ``username``, limiting results
        to a maximum of ``count``.
        """
        required_param(username, "get_user_tweets")
        tweets = []
        try:
            # Pulling individual tweets from query
            for tweet in self.api.user_timeline(id=username, count=count):
                # Adding to list that contains all tweets
                tw = Tweet(
                    created_at=tweet.created_at,
                    id=tweet.id,
                    tweet_id_str=tweet.id_str,
                    text=tweet.text,
                    in_reply_to_screen_name=tweet.in_reply_to_screen_name,
                    lang=tweet.lang,
                    name=tweet.user.name,
                    screen_name=tweet.user.screen_name,
                    hashtags=[ht["text"] for ht in tweet.entities["hashtags"]],
                    is_truncated=tweet.truncated,
                    favorite_count=tweet.favorite_count,
                    retweeted=tweet.retweeted,
                    retweet_count=tweet.retweet_count,
                )
                tweets.append(tw)
        except TweepError as e:
            self.logger.warning("Twitter timeline failed: %s", str(e))
        return tweets

    def text_search_tweets(
        self,
        query: str = None,
        count: int = 100,
        geocode: str = None,
        lang: str = None,
        locale: str = None,
        result_type: str = "mixed",
        until: str = None,
        since_id: str = None,
        max_id: str = None,
    ) -> list:
        """Search tweets filtered by given parameters.

        ``query`` is a search string of 500 characters maximum, including operators

        ``count`` is the maximum number of tweets

        ``geocode`` is the physical location of the user, as latitude/longitude

        ``lang`` is the language code of tweets being searched

        ``locale`` is the language of the query being sent

        ``result_type`` defines which types of tweets are preferred

        Supported result types:
        - mixed: include both popular and real time results in the response (default)
        - recent: return only the most recent results in the response
        - popular: return only the most popular results in the response

        ``until`` limits tweets to ones created before given date

        ``since_id`` is the minimum ID of returned tweets

        ``max_id`` is the maximum ID of returned wtweets

        Returns a list of ``Tweet`` class instances.
        """
        required_param(query, "text_search_tweets")
        tweets = []
        try:
            # Pulling individual tweets from query
            for tweet in self.api.search(
                q=query,
                count=count,
                geocode=geocode,
                lang=lang,
                locale=locale,
                result_type=result_type,
                until=until,
                since_id=since_id,
                max_id=max_id,
            ):
                tw = Tweet(
                    created_at=tweet.created_at,
                    id=tweet.id,
                    tweet_id_str=tweet.id_str,
                    text=tweet.text,
                    in_reply_to_screen_name=tweet.in_reply_to_screen_name,
                    lang=tweet.lang,
                    name=tweet.user.name,
                    screen_name=tweet.user.screen_name,
                    hashtags=[ht["text"] for ht in tweet.entities["hashtags"]],
                    is_truncated=tweet.truncated,
                    favorite_count=tweet.favorite_count,
                    retweeted=tweet.retweeted,
                    retweet_count=tweet.retweet_count,
                )
                tweets.append(tw)
        except TweepError as e:
            self.logger.warning("Twitter search failed: %s", str(e))
        return tweets

    def get_user_profile(self, username: str = None) -> dict:
        """Get Twitter profile with ``username``.

        Returns a dictionary of profile attributes.
        """
        required_param(username, "get_user_profile")
        try:
            profile = self.api.get_user(username)
            data = profile._json  # pylint: disable=W0212
            notebook_json(data)
            return data
        except TweepError:
            return None

    def tweet(self, content: str = None) -> None:
        """Make a tweet with `content` as text. """
        required_param(content, "tweet")
        self.api.update_status(content)

    def like(self, tweet: Tweet = None) -> bool:
        """Like a given ``tweet``.

        Tweet should be an instance of the ``Tweet`` class returned from other
        keywords.

        Returns True if tweet was liked, otherwise False.
        """
        required_param(tweet, "like")
        try:
            self.api.create_favorite(tweet.id)
            return True
        except TweepError:
            self.logger.warning(
                'Could not like tweet "%s" by user "%s"',
                tweet.text,
                tweet.screen_name,
            )
            return False

    def unlike(self, tweet: Tweet = None) -> bool:
        """Unlike a given ``tweet``.

        Tweet should be an instance of the ``Tweet`` class returned from other
        keywords.

        Returns True if tweet was unliked, otherwise False.
        """
        required_param(tweet, "unlike")
        try:
            self.api.destroy_favorite(tweet.id)
            return True
        except TweepError:
            self.logger.warning(
                'Could not unlike tweet "%s" by user "%s"',
                tweet.text,
                tweet.screen_name,
            )
            return False

    def follow(self, user: str = None) -> bool:
        """Follow Twitter ``user`` with matching screen name.

        Returns True if followed successfully, otherwise False.
        """
        required_param(user, "follow")
        try:
            self.api.create_friendship(user)
            return True
        except TweepError:
            self.logger.warning("Could not follow user: %s", user)
            return False

    def unfollow(self, user: str = None) -> bool:
        """Unfollow Twitter ``user`` with matching screen name.

        Returns True if unfollowed successfully, otherwise False.
        """
        required_param(user, "unfollow")
        try:
            self.api.destroy_friendship(user)
            return True
        except TweepError:
            self.logger.warning("Could not unfollow user: %s", user)
            return False
