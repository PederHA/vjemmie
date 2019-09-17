from discord.ext import commands
import discord
from cogs.base_cog import BaseCog
from datetime import datetime, timedelta
from time import perf_counter, time
import json
from functools import partial
from typing import Union, List

from itertools import islice

from github import Github, GithubObject, Commit

from utils.checks import owners_only
from utils.datetimeutils import format_time_difference
from botsecrets import GITHUB_TOKEN

class StatsCog(BaseCog):
    """Commands and methods for gathering bot statistics."""

    EMOJI = ":chart_with_upwards_trend:"

    def __init__(self, bot: commands.Bot) -> None:
        super().__init__(bot)
        self.bot.start_time = datetime.now()
        self.github = Github(GITHUB_TOKEN)

    def get_bot_uptime(self, type: Union[dict, str]=dict) -> str:
        up = format_time_difference(self.bot.start_time)
        if type == dict:
            return up
        elif type == str:
            up_fmt = lambda dur, unit: f"{dur}{unit} " if dur else ""
            uptime = (f"{up_fmt(up['days'], 'd')}"
                    f"{up_fmt(up['hours'], 'h')}"
                    f"{up_fmt(up['minutes'], 'm')}"
                    f"{up_fmt(up['seconds'], 's')}")
            return uptime       
        else:
            raise TypeError("Return type must be 'str' or 'dict'")
    
    @commands.command(name="uptime", aliases=["up"])
    async def uptime(self, ctx: commands.Context) -> str:
        """Bot uptime."""
        up = self.get_bot_uptime(type=str)
        await ctx.send(f"Bot has been up for {up}")
        return up # Band-aid fix to simplify access to bot uptime from other cogs
        
    @commands.command(name="get_players")
    @owners_only()
    async def get_players(self, ctx) -> None:
        """Display active audio players."""
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
    async def changelog(self, 
                        ctx: commands.Context, 
                        days: int=0, 
                        *, 
                        rtn_type: Union[str, list, None]=None
                        ) -> Union[List[Commit.Commit], str, None]:
        """Display git commit log"""
        commits = await self.get_commits("PederHA/vjemmie", days)
        
        # Format commit hash + message
        out_commits = "\n".join(
            [
            f"[`{commit.sha[:7]}`]({commit.html_url}): {commit.commit.message.splitlines()[0]}"
            for commit in commits
            ]
        )
        
        await self.send_embed_message(ctx, "Commits", out_commits, color=0x24292e)
    
    async def get_commits(self, repo: str, days: int) -> List[Commit.Commit]:
        # Limit number of days to get commits from
        if days > 7:
            raise ValueError("Number of days cannot exceed 7!")
        
        # Get repo
        repo = self.github.get_repo(repo)

        # Fetch commits non-blocking
        since = datetime.now() - timedelta(days=days) if days else GithubObject.NotSet
        to_run = partial(repo.get_commits, since=since)
        _c = await self.bot.loop.run_in_executor(None, to_run)
        
        if days:
            commits = list(_c)
        else:
            # Get 5 most recent commits if no days argument
            commits = list(islice(_c, 5))
        
        if not commits:
            if days:
                # Wrong type but w/e ill fix later
                raise AttributeError(
                    f"No changes have been made in the past {days} days!"
                    )
            else:
                raise AttributeError(
                    "Could not fetch changes from GitHub, try again later!"
                    )

        return commits
       
    @commands.command(name="commits")
    async def commits(self, ctx: commands.Context) -> None:
        """Display number of commits made past week"""
        commits = await self.get_commits("PederHA/vjemmie", days=7)
        n_commits = len(commits)
        await ctx.send(f"{n_commits} commits have been made the past week.")

    @commands.command(name="ping")
    async def ping(self, ctx: commands.Context) -> str:  
        ping_ms = self.get_bot_ping_ms()
        await ctx.send(f"Ping: {ping_ms}ms")

    def get_bot_ping_ms(self) -> int:
        return round(self.bot.ws.latency*100)