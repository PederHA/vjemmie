import asyncio
import sys
from datetime import datetime, timedelta
from typing import Optional, Union, List

import discord
import spotipy
from praw import Reddit
from discord.ext import commands
from github import Github
from googleapiclient.discovery import build
from spotipy.oauth2 import SpotifyClientCredentials
from mwthesaurus import MWClient

from ..config import YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION
from ..utils import spotify, youtube
from ..utils.checks import admins_only, load_blacklist, save_blacklist
from ..utils.printing import eprint
from . import reddit_cog, stats_cog, fun_cog
from .base_cog import BaseCog, EmbedField


class BotSetupCog(BaseCog):
    def __init__(self, bot) -> None:
        self.bot = bot
        self.setup_youtube()
        self.setup_spotify()
        self.setup_github()
        self.setup_reddit()
        self.setup_mwthesaurus()
            
    def setup_spotify(self) -> None:
        if not all(c for c in [
            self.bot.secrets.SPOTIFY_CLIENT_SECRET,
            self.bot.secrets.SPOTIFY_CLIENT_ID
            ]
        ):
            eprint(
                "Spotify Credentials are missing.\n"
                "How to fix:\n"
                "1. Create a Spotify User Account\n"
                "2. Log into your Dashboard: https://developer.spotify.com/dashboard\n"
                "3. Create an Application\n"
                "4. Retrieve Client ID and Client Secret\n"
            )
            return self.remove_commands(["spotify"])

        spotify.spotify = spotipy.Spotify(
            client_credentials_manager=SpotifyClientCredentials(
                client_id=self.bot.secrets.SPOTIFY_CLIENT_ID, 
                client_secret=self.bot.secrets.SPOTIFY_CLIENT_SECRET
            )
        )
    def setup_youtube(self) -> None:
        if not self.bot.secrets.YOUTUBE_API_KEY:
            eprint(
                "YouTube API Key is missing.\n"
                "How to fix:\n"
                "1. Go to https://console.developers.google.com/apis/api/youtube.googleapis.com/credentials\n"
                "2. Create a project\n"
                "3. Enable YouTube Data API v3\n"
                "4. Create an API Key"
            )
            return self.remove_commands(["yt"])
         
        youtube.youtube = build(
            YOUTUBE_API_SERVICE_NAME,
            YOUTUBE_API_VERSION,
            developerKey=self.bot.secrets.YOUTUBE_API_KEY
        )

    def setup_github(self) -> None:
        if not self.bot.secrets.GITHUB_TOKEN:
            eprint(
                "GitHub personal access token is missing.\n"
                "How to fix:\n"
                "1. Go to https://github.com/settings/tokens\n"
                "2. Generate new token\n"
                "3. Enable repo:status\n"
                "4. Generate personal access token"
            )
            return self.remove_commands(["changelog", "commits"])
        
        stats_cog.githubclient = Github(self.bot.secrets.GITHUB_TOKEN)

    def setup_reddit(self) -> None:
        if not all(c for c in [
            self.bot.secrets.REDDIT_ID,
            self.bot.secrets.REDDIT_SECRET,
            self.bot.secrets.REDDIT_USER_AGENT,
            ]
        ):
            eprint(
                "Reddit API credentials are missing.\n"
                "How to fix:\n"
                "1. Go to https://old.reddit.com/prefs/apps/\n"
                "2. Create a new Reddit App\n"
                "3. Retrieve its ID and Secret key"
            )
            return self.remove_cog("RedditCog")
        reddit_cog.reddit = Reddit(
            client_id=self.bot.secrets.REDDIT_ID,
            client_secret=self.bot.secrets.REDDIT_SECRET,
            user_agent=self.bot.secrets.REDDIT_USER_AGENT,
        )

    def setup_mwthesaurus(self) -> None:
        if not (self.bot.secrets.MERRIAM_WEBSTER_KEY):
            eprint(
                "Merriam-Webster API credentials are missing.\n"
                "How to fix:\n"
                "1. Go to https://dictionaryapi.com/register/index\n"
                "2. Create a new account & request college thesaurus key"
            )
            return self.remove_commands(["synonyms"])
        fun_cog.mw = MWClient(key=self.bot.secrets.MERRIAM_WEBSTER_KEY)

    def remove_commands(self, commands: List[str]) -> None:
        for cmd in commands:
            eprint(f"Disabling command '{self.bot.command_prefix}{cmd}'")
            self.bot.remove_command(cmd)

    def remove_cog(self, cog: str) -> None:
        if not self.bot.get_cog(cog):
            eprint(
                f"BotSetupCog attempted to disable cog '{cog}', "
                f"but no such cog exists."
            )
            return
        eprint(f"Disabling cog '{cog}'")
        self.bot.remove_cog(cog)
