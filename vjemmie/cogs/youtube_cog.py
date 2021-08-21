import time
import urllib.request
from urllib.parse import urlencode

import bs4 as bs
from discord.ext import commands

from ..utils.exceptions import CommandError
from .base_cog import BaseCog


class YouTubeCog(BaseCog):
    """YouTube commands."""

    EMOJI = ":tv:"
    DISABLE_HELP = True

    @commands.command(
        name="youtube",
        aliases=["yt", "utube"],
        description="YouTube search that returns top result for search query.",
    )
    async def youtube(self, ctx: commands.Context, *search_query: str):
        """Retired for now"""
        raise CommandError(
            "Command is unavailable right now due to changes to YouTube's search results."
        )

        start_time = time.time()
        if not search_query:
            raise CommandError("A search query is required!")
        url = "https://www.youtube.com/results?{}".format(
            urlencode({"search_query": " ".join(search_query)})
        )
        sauce = urllib.request.urlopen(url).read()
        soup = bs.BeautifulSoup(sauce, "html.parser")

        link = (
            soup.find("div", class_="yt-lockup-thumbnail contains-addto")
            .find("a", class_=" yt-uix-sessionlink spf-link ")
            .get("href")
        )

        exetime = time.time() - start_time
        exetime = "{0:.1f}".format(exetime)

        await ctx.send(("https://youtube.com{}").format(link))
