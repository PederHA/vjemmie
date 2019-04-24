from discord.ext import commands
import discord
from cogs.base_cog import BaseCog
from datetime import datetime, timedelta
from time import perf_counter, time
import json
from functools import partial
from typing import Union

from itertools import islice

from github import Github, GithubObject

from ext.checks import owners_only
from botsecrets import GITHUB_TOKEN

class StatsCog(BaseCog):
    """Commands and methods for gathering bot statistics."""

    EMOJI = ":chart_with_upwards_trend:"

    def __init__(self, bot: commands.Bot) -> None:
        super().__init__(bot)
        self.bot.start_time = datetime.now()
        self.github = Github(GITHUB_TOKEN)

    @commands.command(name="uptime")
    async def uptime(self, ctx: commands.Context) -> None:
        """Bot uptime."""
        up = datetime.now() - self.bot.start_time
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
        """ADMIN ONLY: Display active audio players."""
        sound_cog = self.bot.get_cog("SoundCog")
        players = sound_cog.players
      
        out = []
        for gid, player in players.items():
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
    
    @commands.command(name="changelog")
    @commands.cooldown(rate=1, per=10, type=commands.BucketType.guild)
    async def changelog(self, ctx: commands.Context, days: int=0, *, rtn: bool=False) -> Union[list, str]:
        """Display git commmit log"""
        # Limit number of days to get commits from
        if days > 7:
            raise ValueError("Number of days cannot exceed 7!")
        
        # Get repo
        repo = self.github.get_repo("PederHA/vjemmie")

        # Get commits
        since = datetime.now() - timedelta(days=days) if days else GithubObject.NotSet
        to_run = partial(repo.get_commits, since=since)
        _c = await self.bot.loop.run_in_executor(None, to_run)
        
        if days:
            commits = list(_c)
        else:
            # Get 5 most recent commits if no days argument
            commits = list(islice(_c, 5))

        # Format commit hash + message
        n = "\n"
        out_commits = "\n".join(
            [
            f"[`{commit.sha[:7]}`]({commit.html_url}): {commit.commit.message.split(n, 1)[0]}"
            for commit in commits
            ]
        )

        await self.send_embed_message(ctx, "Commits", out_commits, color=0x24292e)

        if rtn:
            # List of github.Commit objects
            return commits
        else:
            # Formatted hash: description string
            return out_commits
    
    @commands.command(name="commits")
    async def commits(self, ctx: commands.Context) -> None:
        """Display number of commits made past week"""
        commits = await ctx.invoke(self.changelog, 7, rtn=True)
        n_commits = len(commits)
        await ctx.send(f"{n_commits} commits have been made the past week.")