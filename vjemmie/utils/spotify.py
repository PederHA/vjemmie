from functools import partial
from typing import Dict, Tuple

import spotipy
from discord.ext.commands.bot import Bot
from discord.ext.commands.context import Context
from spotipy import Spotify
from spotipy.oauth2 import SpotifyClientCredentials

from ..botsecrets import secrets
from .exceptions import CommandError


def _get_spotify_client(client_id: str, client_secret: str) -> Spotify:
    return Spotify(
        client_credentials_manager=SpotifyClientCredentials(
            client_id=client_id, client_secret=client_secret
        )
    )


async def get_spotify_client(ctx: Context) -> Spotify:
    client = _clients.get(ctx.guild.id)
    if not client:
        to_run = partial(
            SpotifyClient,
            ctx.bot,
            secrets.SPOTIFY_CLIENT_ID,
            secrets.SPOTIFY_CLIENT_SECRET,
        )
        client = await ctx.bot.loop.run_in_executor(None, to_run)  # type: SpotifyClient
        _clients[ctx.guild.id] = client
    return client


class SpotifyClient:
    def __init__(self, bot: Bot, client_id: str, client_secret: str) -> None:
        self.bot = bot
        self.client = _get_spotify_client(client_id, client_secret)

    async def get_song_info(self, arg: str) -> Tuple[str, str, str]:
        """Fetches artist, song and album from a Spotify URL or URI."""
        track_id = await self.get_track_id(arg)
        track = await self.bot.loop.run_in_executor(None, self.client.track, track_id)
        artists = ", ".join([artist["name"] for artist in track["artists"]])
        song = track["name"]
        album = track["album"]["name"]

        return artists, song, album

    async def get_track_id(self, arg: str) -> str:
        if arg.startswith("spotify:track:"):
            track_id = arg.split("spotify:track:")[1]
        elif arg.startswith("https://open.spotify.com/track/"):
            track_id = arg.split("https://open.spotify.com/track/")[1].split("?")[0]
        elif arg.startswith("spotify:album:"):
            raise CommandError("Spotify albums are not supported!")
        elif arg.startswith("spotify:playlist:"):
            raise CommandError("Spotify playlists are not supported!")
        else:
            raise CommandError("Unrecognized spotify URI/URL")
        return track_id


_clients: Dict[int, SpotifyClient] = {}
