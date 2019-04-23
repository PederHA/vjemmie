from discord.ext import commands
import discord
from cogs.base_cog import BaseCog
from datetime import datetime
from time import perf_counter, time
import json

from itertools import islice

from github import Github

from ext.checks import owners_only
from botsecrets import GITHUB_TOKEN

class StatsCog(BaseCog):
    """Commands and methods for gathering bot statistics."""

    EMOJI = ":chart_with_upwards_trend:"

    def __init__(self, bot: commands.Bot) -> None:
        super().__init__(bot)
        self.START_TIME = datetime.now()
        self.github = Github(GITHUB_TOKEN)

    @commands.command(name="uptime")
    async def uptime(self, ctx: commands.Context) -> None:
        up = datetime.now() - self.START_TIME
        days = up.days
        hours, remainder = divmod(up.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        # If you want to take into account fractions of a second
        seconds += round(up.microseconds / 1e6)
        
        # Returns empty string if number is 0
        up_fmt = lambda dur, unit: f"{dur}{unit} " if dur else ""

        await ctx.send("Bot has been up for " 
                       f"{up_fmt(days, 'd')}"
                       f"{up_fmt(hours, 'h')}"
                       f"{up_fmt(minutes, 'm')}"
                       f"{up_fmt(seconds, 's')}")

    @commands.command(name="get_players")
    @owners_only()
    async def get_players(self, ctx) -> None:
        sound_cog = self.bot.get_cog("SoundCog")
        players = sound_cog.players
        #with open("out/audioplayers.json", "r") as f:
        #    players = json.load(f)
        
        out = []
        for gid, player in players.items():
            #embed_body = ( 
            #        f"**Created at**: {player['created_at']}\n"
            #        f"**Currently playing**: {player['current']}"
            #        f"**Guild ID**: {gid}\n"
            #        )
            embed_body = ( 
                    f"**Created at**: {player.created_at}\n"
                    f"**Currently playing**: {player.current.title if player.current else None}\n"
                    f"**Guild ID**: {gid}\n"
                    )            
            out.append((str(self.bot.get_guild(gid)), embed_body))

        # Post active players
        if out:
            for gname, o in out:
                await self.send_embed_message(ctx, gname, o, footer=False)
        else:
            await ctx.send("No active audio players")

    @commands.command(name="commits")
    async def git_commits(self, ctx: commands.Context) -> None:
        # Get repo
        repo = self.github.get_repo("PederHA/vjemmie")

        # Only retrieve 5 most recent commits 
        commits = list(islice(repo.get_commits(), 5))
        
        # Format commit hash + message
        out_commits = "\n".join(
            [
            f"[`{commit.sha[:7]}`]({commit.html_url}): {commit.commit.message}"
            for commit in commits
            ]
        )

        await self.send_embed_message(ctx, "Commits", out_commits, color=0x24292e)