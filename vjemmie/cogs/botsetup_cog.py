from typing import List

import spotipy
from github import Github
from googleapiclient.errors import HttpError
from loguru import logger
from mwthesaurus import MWClient
from praw import Reddit

from ..botsecrets import secrets
from ..config import config
from ..db import init_pydantic_validator
from ..utils.merriamwebster import init_mw
from ..utils.spotify import _get_spotify_client
from ..utils.youtube import _get_youtube_client
from . import reddit_cog, stats_cog
from .base_cog import BaseCog


class BotSetupCog(BaseCog):
    def __init__(self, bot) -> None:
        self.bot = bot

        # DB
        init_pydantic_validator(bot)

        # External APIs
        self.setup_youtube()
        self.setup_spotify()
        self.setup_github()
        self.setup_reddit()
        self.setup_mwthesaurus()

    def setup_spotify(self) -> None:
        if not all(
            c
            for c in [
                secrets.SPOTIFY_CLIENT_SECRET,
                secrets.SPOTIFY_CLIENT_ID,
            ]
        ):
            logger.warning(
                "Spotify Credentials are missing.\n"
                "How to fix:\n"
                "1. Create a Spotify User Account\n"
                "2. Log into your Dashboard: https://developer.spotify.com/dashboard\n"
                "3. Create an Application\n"
                "4. Retrieve Client ID and Client Secret\n"
            )
            return self.remove_commands(["spotify"])

        # try to build client
        _get_spotify_client(secrets.SPOTIFY_CLIENT_ID, secrets.SPOTIFY_CLIENT_SECRET)

    def setup_youtube(self) -> None:
        err_msg = (
            "YouTube API Key is missing or invalid.\n"
            "How to fix:\n"
            "1. Go to https://console.developers.google.com/apis/api/youtube.googleapis.com/credentials\n"
            "2. Create a project\n"
            "3. Enable YouTube Data API v3\n"
            "4. Create an API Key"
        )
        if not secrets.YOUTUBE_API_KEY:
            logger.warning(err_msg)
            return self.remove_commands(["yt"])

        try:
            # try to build a YouTube client
            _get_youtube_client(
                config.YOUTUBE_API_SERVICE_NAME,
                config.YOUTUBE_API_VERSION,
                secrets.YOUTUBE_API_KEY,
            )
        except HttpError as e:
            if b"400" in e.content:
                logger.warning(err_msg)
                return self.remove_commands(["yt"])
            else:
                raise

    def setup_github(self) -> None:
        if not secrets.GITHUB_TOKEN:
            logger.warning(
                "GitHub personal access token is missing.\n"
                "How to fix:\n"
                "1. Go to https://github.com/settings/tokens\n"
                "2. Generate new token\n"
                "3. Enable repo:status\n"
                "4. Generate personal access token"
            )
            return self.remove_commands(["changelog", "commits"])

        stats_cog.githubclient = Github(secrets.GITHUB_TOKEN)

    def setup_reddit(self) -> None:
        if not all(
            c
            for c in [
                secrets.REDDIT_ID,
                secrets.REDDIT_SECRET,
                secrets.REDDIT_USER_AGENT,
            ]
        ):
            logger.warning(
                "Reddit API credentials are missing.\n"
                "How to fix:\n"
                "1. Go to https://old.reddit.com/prefs/apps/\n"
                "2. Create a new Reddit App\n"
                "3. Retrieve its ID and Secret key"
            )
            return self.remove_cog("RedditCog")
        reddit_cog.reddit = Reddit(
            client_id=secrets.REDDIT_ID,
            client_secret=secrets.REDDIT_SECRET,
            user_agent=secrets.REDDIT_USER_AGENT,
        )

    def setup_mwthesaurus(self) -> None:
        if not (secrets.MERRIAM_WEBSTER_KEY):
            logger.warning(
                "Merriam-Webster API credentials are missing.\n"
                "How to fix:\n"
                "1. Go to https://dictionaryapi.com/register/index\n"
                "2. Create a new account & request college thesaurus key"
            )
            return self.remove_commands(["synonyms"])
        init_mw(secrets.MERRIAM_WEBSTER_KEY)

    def remove_commands(self, commands: List[str]) -> None:
        if not commands:
            return  # Just silently ignore empty list. NOTE: bad?
        s = "s" if len(commands) > 1 else ""
        cmds = ", ".join([f"'{self.bot.command_prefix}{cmd}'" for cmd in commands])
        logger.info(f"Disabling command{s} {cmds}")
        for cmd in commands:
            self.bot.remove_command(cmd)

    def remove_cog(self, cog: str) -> None:
        if not self.bot.get_cog(cog):
            logger.error(
                f"BotSetupCog attempted to disable cog '{cog}', "
                f"but no such cog exists."
            )
            return
        logger.info(f"Disabling cog '{cog}'")
        self.bot.remove_cog(cog)
