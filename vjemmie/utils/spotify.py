from typing import Tuple

import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

from .exceptions import CommandError


spotify: spotipy.Spotify = None # initialized by botsetup_cog


def get_spotify_song_info(arg: str) -> Tuple[str, str, str]:
    """Fetches artist, song and album from a Spotify URL or URI."""
    track_id = get_spotify_track_id(arg)

    track = spotify.track(track_id)
    artists = ", ".join([artist["name"] for artist in track["artists"]])
    song = track["name"]
    album = track["album"]["name"]

    return artists, song, album


def get_spotify_track_id(arg: str) -> str:
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
