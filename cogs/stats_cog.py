import asyncio
import json
from datetime import datetime, timedelta
from functools import partial
from collections import defaultdict, Counter
from itertools import islice
from time import perf_counter, time
from typing import List, Union

import discord
from discord.ext import commands
from github import Commit, Github, GithubObject

from botsecrets import GITHUB_TOKEN
from cogs.base_cog import BaseCog
from config import STATS_DIR
from utils.caching import get_cached
from utils.checks import owners_only
from utils.exceptions import CommandError
from utils.datetimeutils import format_time_difference
from utils.serialize import dump_json


CMD_USAGE_FILE = f"{STATS_DIR}/commandusage.json"

class StatsCog(BaseCog):
    """Commands and methods for gathering bot statistics."""

    EMOJI = ":chart_with_upwards_trend:"
    DIRS = [STATS_DIR]
    FILES = [CMD_USAGE_FILE]

    def __init__(self, bot: commands.Bot) -> None:
        super().__init__(bot)
        self.bot.start_time = datetime.now()
        self.github = Github(GITHUB_TOKEN)
        self._init_commands_counter()

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        await self.cmd_usage_loop()
    
    @commands.Cog.listener()
    async def on_command_completion(self, ctx: commands.Context) -> None:
        await self.log_command_usage(ctx)
    
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

    def _init_commands_counter(self) -> None:
        self.commands = defaultdict(Counter)

    async def log_command_usage(self, ctx: commands.Context) -> None:
        self.commands[ctx.guild.id][ctx.command.qualified_name] += 1
    
    def get_top_commands(self, guild_id: Union[str, int]=None) -> None:
        """Get top commands for all guilds or a specific guild."""
        u = get_cached(CMD_USAGE_FILE)
        if guild_id:
            usage = u[str(guild_id)] # JSON only support str keys
        else:
            usage = u
        return usage

    def get_command_usage(self, guild_id: Union[str, int], command: str) -> int:
        """Get number of times a command has been used in a specific guild."""
        try:
            usage = self.get_top_commands(guild_id=str(guild_id))
            return usage[command]
        except KeyError:
            return 0        

    async def _dump_command_usage(self) -> None:
        usage = self.get_top_commands()
        for guild_id, counter in self.commands.items():
            guild_id = str(guild_id) # NEEDED?
            try:
                usage[guild_id]
            except KeyError:
                usage[guild_id] = {}
            finally:
                usage[guild_id] = defaultdict(int, usage[guild_id])
            for cmd, val in counter.items():
                usage[guild_id][cmd] += val
        dump_json(CMD_USAGE_FILE, usage)

    async def cmd_usage_loop(self) -> None:
        while True:
            await self._dump_command_usage()
            self._init_commands_counter()
            await asyncio.sleep(60)

    @commands.command(name="topcommands", aliases=["topc"])
    async def top_commands(self, ctx: commands.Context, n_commands: int=10) -> None:
        if not ctx.guild:
            raise CommandError("This command is not supported in DMs!")
        
        try:
            cmds = self.get_top_commands(guild_id=ctx.guild.id)
        except KeyError:
            raise CommandError("No commands have been used in this server!")
        else:
            _c = [(k, v) for k, v in cmds.items()]
            cmds = sorted(_c, key=lambda d: d[1], reverse=True)
        
        if n_commands >= 3:
            try:
                cmds = cmds[:n_commands]
            except TypeError:
                raise CommandError("Number of commands must be an integer.")
        
        description = "\n".join([
            f"`{self.bot.command_prefix}{cmd.ljust(20, self.EMBED_FILL_CHAR)}:` {n}"
            for (cmd, n) in cmds
        ])

        await self.send_embed_message(ctx, title=f"Top {n_commands} Commands for {ctx.guild.name}", description=description)

    @commands.command(name="uptime", aliases=["up"])
    async def uptime(self, ctx: commands.Context) -> str:
        """Bot uptime."""
        up = self.get_bot_uptime(type=str)
        await ctx.send(f"Bot has been up for {up}")
        return up # NOTE: I think this is LITERALLY just for TestCog. Remove?
        
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
