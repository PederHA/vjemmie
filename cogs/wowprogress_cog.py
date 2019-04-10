import bs4 as bs
from discord.ext import commands
import discord

import time
from urllib.parse import urlencode
import urllib.request
from cogs.base_cog import BaseCog

class WoWProgressCog(BaseCog):
    """WoWProgress commands."""

    @commands.command(name="wp",
                      aliases=["wowp"],
                      description="Searches WoWprogress for a given guild name, and returns top result.")
    async def wowprogress(self, ctx: commands.Context, *args: str):
        try:
            start_time = time.time()
            url = ("https://www.wowprogress.com/search?{}&type=guild".format(
                urlencode({'q': ' '.join(args)})
            ))
            
            sauce = urllib.request.urlopen(url).read()
            soup = bs.BeautifulSoup(sauce, 'html.parser')

            # Finds the top search result and fetches url to guild page
            top_result = soup.find(
                "a", {"class": lambda L: L and L.startswith("guild")})

            # Sends error message to the channel in case a guild cannot be found
            if top_result == None:
                await ctx.send("Couldn't find guild!")

            # Top result is cast to string, then appended to wowprogress URL
            # to create the full website URL to the guild page
            top_result = str(top_result.get("href"))
            guild_wp_url = "https://wowprogress.com" + top_result

            # Scrapes the resulting URL from the top result
            sauce = urllib.request.urlopen(guild_wp_url).read()
            soup = bs.BeautifulSoup(sauce, "html.parser")

            # Raids Per Week
            raids_per_week = soup.find("div", class_="raids_week").string.split(": ", 1)[1]

            # Exception for guilds with unknown raid days
            # Nothing here yet.

            # Guild name
            guild_name = soup.find("title").string.partition("@")[0].split("Guild ", 1)[1]

            # Progression
            progress = soup.find("span", class_="innerLink ratingProgress").find("b").string

            # World Rank
            world_rank = soup.find("span", {"class": lambda L: L and L.startswith("rank")}).string

            # Calculate execution time
            exetime = (time.time()-start_time)
            exetime = "{0:.1f}".format(exetime)

            # TODO: Markdown formatting (bold).    
            await ctx.send(guild_wp_url + ("\n\n```markdown\n"
                                            f"Guild Name: {guild_name}\n"
                                            f"Progress: {progress}\n"
                                            f"World Rank: {world_rank}\n"
                                            f"Raids Per Week: {raids_per_week}\n"
                                            "```\n"
                                            f"🤖Command executed in {exetime} seconds"))     
        except Exception:
            # Lazy solution, but this will be the correct error message to return in 99% of cases.
            await ctx.send("Guild is inactive.")
