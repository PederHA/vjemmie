from pathlib import Path

import discord
import youtube_dl
from discord.ext import commands

from .base_cog import BaseCog
from ..config import TEMP_DIR
from ..utils.checks import disabled_cmd

ytdlopts = {
    'format': 'best',
    'outtmpl': f'{TEMP_DIR}/%(title)s.%(ext)s',
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0'
}

class VideoCog(BaseCog):
    """Video commands."""
    EMOJI = ":video_camera:"

    DIRS = [TEMP_DIR]
    MAX_VIDEO_LEN_SEC = 30
    
    @commands.command(name="webm")
    async def webm(self, ctx: commands.Context, url: str, start: int=0, stop: int=30) -> None:
        if start < 0:
            start = 0
        if stop - start > 30:
            raise ValueError(
                f"Maximum video length is {self.MAX_VIDEO_LEN_SEC} seconds!"
                )
        path = await self.bot.loop.run_in_executor(None, self._get_video, url)
        print(path)

    # TODO: contextmanager that ensures video is deleted afterwards?

    def _get_video(self, url: str) -> Path:
        """Downloads a video, returns path of downloaded video."""
        with youtube_dl.YoutubeDL(ytdlopts) as ytdl:
            info = ytdl.extract_info(url, download=True)
            res = ytdl.prepare_filename(info)
            return Path(res)
