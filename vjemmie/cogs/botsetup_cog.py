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
from googleapiclient.errors import HttpError
from spotipy.oauth2 import SpotifyClientCredentials
from mwthesaurus import MWClient

from ..db import add_db
from ..config import YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, MAIN_DB
from ..utils import spotify, youtube
from ..utils.checks import admins_only, load_blacklist, save_blacklist
from ..utils.printing import eprint
from . import reddit_cog, stats_cog, fun_cog
from .base_cog import BaseCog, EmbedField

QUIET = False # TODO: Make this a of persistent user-defined value

class BotSetupCog(BaseCog):
    def __init__(self, bot) -> None:
        self.print = eprint
        if QUIET:
            def printer(*args, **kwargs):
                pass
            self.print = printer
        
        self.bot = bot

        # APIs
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
            self.print(
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
        err_msg = (
                "YouTube API Key is missing or invalid.\n"
                "How to fix:\n"
                "1. Go to https://console.developers.google.com/apis/api/youtube.googleapis.com/credentials\n"
                "2. Create a project\n"
                "3. Enable YouTube Data API v3\n"
                "4. Create an API Key"
            )
        if not self.bot.secrets.YOUTUBE_API_KEY:
            self.print(err_msg)
            return self.remove_commands(["yt"])
        
        try:  
            youtube.youtube = build(
                YOUTUBE_API_SERVICE_NAME,
                YOUTUBE_API_VERSION,
                developerKey=self.bot.secrets.YOUTUBE_API_KEY
            )
        except HttpError as e:
            if b"400" in e.content:
                self.print(err_msg)
                return self.remove_commands(["yt"])
            else:
                raise

    def setup_github(self) -> None:
        if not self.bot.secrets.GITHUB_TOKEN:
            self.print(
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
            self.print(
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
            self.print(
                "Merriam-Webster API credentials are missing.\n"
                "How to fix:\n"
                "1. Go to https://dictionaryapi.com/register/index\n"
                "2. Create a new account & request college thesaurus key"
            )
            return self.remove_commands(["synonyms"])
        fun_cog.mw = MWClient(key=self.bot.secrets.MERRIAM_WEBSTER_KEY)

    def remove_commands(self, commands: List[str]) -> None:
        if not commands:
            return # Just silently ignore empty list. NOTE: bad?
        s = 's' if len(commands)>1 else ''
        cmds = ", ".join([f"'{self.bot.command_prefix}{cmd}'" for cmd in commands])
        print(f"Disabling command{s} {cmds}", end="\n\n")
        for cmd in commands:
            self.bot.remove_command(cmd)

    def remove_cog(self, cog: str) -> None:
        if not self.bot.get_cog(cog):
            self.print(
                f"BotSetupCog attempted to disable cog '{cog}', "
                f"but no such cog exists."
            )
            return
        self.print(f"Disabling cog '{cog}'")
        self.bot.remove_cog(cog)
