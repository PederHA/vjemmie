import asyncio
from datetime import datetime, timedelta
from typing import Optional, Union
import sys

import discord
import spotipy
from discord.ext import commands
from googleapiclient.discovery import build
from spotipy.oauth2 import SpotifyClientCredentials

from ..config import YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION
from ..utils.checks import admins_only, load_blacklist, save_blacklist
from ..utils import spotify
from ..utils import youtube
from ..utils.printing import eprint
from .base_cog import BaseCog, EmbedField


class BotSetupCog(BaseCog):
    def __init__(self, bot) -> None:
        self.bot = bot

        self.setup_youtube()
        self.setup_spotify()
            
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
            return self.disable_command("spotify")

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
            return self.disable_command("yt")

        spotify.spotify = spotipy.Spotify(
            client_credentials_manager=SpotifyClientCredentials(
                client_id=self.bot.secrets.SPOTIFY_CLIENT_ID, 
                client_secret=self.bot.secrets.SPOTIFY_CLIENT_SECRET
            )
        )

    def disable_command(self, *cmds) -> None:
        for cmd in cmds:
            eprint(f"Disabling command '{self.bot.command_prefix}{cmd}'\n")
            self.bot.get_command(cmd).enabled = False


        