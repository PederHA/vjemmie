import asyncio
import inspect
import os
import subprocess
import sys
from collections import namedtuple
from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import partial
from pathlib import Path
from typing import Awaitable, Callable, Optional, Union

import discord
import psutil
import websockets
from aiofile import AIOFile
from discord.ext import commands, tasks

from ..config import OWNER_ID, TRUSTED_DIR, TRUSTED_PATH, YES_ARGS
from ..utils.access_control import (Categories, add_trusted_member,
                                    add_trusted_role, get_trusted_members,
                                    get_trusted_roles, remove_trusted_member,
                                    remove_trusted_role)
from ..utils.checks import admins_only, load_blacklist, save_blacklist
from ..utils.exceptions import CommandError
from ..utils.printing import eprint
from .base_cog import BaseCog, EmbedField


@dataclass
class Activity:
    text: str
    callable_: Optional[Callable[..., str]] = None
    prepend_text: bool = True

    async def get_activity(self) -> str:
        r = ""
        if self.callable_:
            if inspect.iscoroutinefunction(self.callable_):
                r = await self.callable_()
            else:
                r = self.callable_()
        
        return f"{self.text}{r}" if self.prepend_text else f"{r}{self.text}"


class AdminCog(BaseCog):
    """Admin commands for administering guild-related bot functionality."""
    FILES = [TRUSTED_PATH]

    # Activity rotation stuff
    ACTIVITY_ROTATION = True
    AC_ROTATION_INTERVAL = 10

    def __init__(self, bot: commands.Bot) -> None:
        super().__init__(bot)

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        """Prints message when cog is ready."""
        print("Bot logged in")
        # Any consise way to check if the loop is in progress?
        # https://discordpy.readthedocs.io/en/latest/ext/tasks/index.html?highlight=tasks%20loop#discord.ext.tasks.Loop.is_running
        # tasks.Loop.is_running() doesn't even seem to exist.
        # This problem could be solved if the loop is started in __init__, but that
        # doesn't work for whatever reason.
        with suppress(RuntimeError):
            self.activity_rotation.start()

    @tasks.loop(seconds=1)
    async def activity_rotation(self) -> None:
        p = self.bot.command_prefix

        activities = [
            Activity(f"{p}about"),
            Activity(f"{p}help"),
            Activity(f"{p}commands"),
            Activity("Uptime: ", partial(self.bot.get_cog("StatsCog").get_bot_uptime, type=str))
        ]

        while self.ACTIVITY_ROTATION: 
            for activity in activities:
                await self._change_activity(await activity.get_activity())
                await asyncio.sleep(self.AC_ROTATION_INTERVAL)

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild) -> None:
        """Called when bot joins a guild."""
        await self.send_log(f"Joined guild {guild.name}", channel_id=self.GUILD_HISTORY_CHANNEL)

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild) -> None:
        """Called when bot leaves a guild."""
        await self.send_log(f"Left guild {guild.name}", channel_id=self.GUILD_HISTORY_CHANNEL)

    async def _change_activity(self, activity_name: str) -> None:
        """Tries to change bot's "playing" status aka. Activity.
        Does not raise an exception on failure to change activity."""
        activity = discord.Game(activity_name)
        try:
            await self.bot.change_presence(activity=activity)
        except discord.InvalidArgument:
            print(f"Invalid activity argument '{activity_name}'")
        except websockets.exceptions.ConnectionClosedError as e:
            print(f"Unable to change activity. {e}")

    @commands.command(name="restart")
    async def restart_bot(self, ctx: commands.Context) -> None:
        subprocess.run(["supervisorctl", "restart", "vjemmie"], shell=True)

    @commands.command(aliases=["ca"])
    @admins_only()
    async def change_activity(self, ctx: commands.Context, activity_name: Optional[str]=None) -> None:
        """Changes bot activity.
        
        Parameters
        ----------
        ctx : `commands.Context`
            Discord context
        activity_name : `Optional[str]`, optional
            Name of activity.
        """
        if activity_name:
            # Disable activity rotation when manually changing bot activity
            self.ACTIVITY_ROTATION = False
            self.activity_rotation.cancel()
            await self._change_activity(activity_name)
        elif not activity_name and not self.ACTIVITY_ROTATION:
            # Run activity rotation
            self.ACTIVITY_ROTATION = True
            self.activity_rotation.start()
        # Do nothing if activity rotation is active and no argument is passed in

    @commands.command(name="serverlist")
    @admins_only()
    async def serverlist(self, ctx: commands.Context) -> None:
        """Sends a list of all guilds the bot is joined to."""
        guilds = "\n".join([guild.name for guild in self.bot.guilds])
        await self.send_embed_message(ctx, "Guilds", guilds)

    @commands.command(name="leave")
    @admins_only()
    async def leave(self, ctx: commands.Context, guild_id: int) -> None:
        """Attempts to leave a Discord Guild (server).
        
        Parameters
        ----------
        ctx : `commands.Context`
            Discord context
        guild_id : `int`
            ID of guild to leave.
        
        Raises
        ------
        `discord.DiscordException`
            Raised if a guild with ID `guild_id` cannot be found.
        `discord.DiscordException`
            Raised if bot is unable to leave the specified guild.
        """
        # Get discord.Guild object for guild with ID guild_id
        guild = self.bot.get_guild(int(guild_id))

        # Raise exception if guild is not found
        if not guild:
            return await ctx.send(f"No guild with ID {guild_id}")

        try:
            await guild.leave()
        except discord.HTTPException:
            raise discord.DiscordException(f"Unable to leave guild {guild.name}")
        else:
            await self.send_log(f"Left guild {guild.name} successfully")

    @commands.command(name="announce",
                      aliases=["send_all", "broadcast"])
    @admins_only()
    async def sendtoall(self, ctx: commands.Context, *, message: str) -> None:
        """
        Attempts to send text message to every server the bot
        is a member of.
        
        Parameters
        ----------
        ctx : `commands.Context`
            Discord context
        message: str
            String to send.
        """
        failed = []
        for guild in self.bot.guilds:
            try:
                channel = guild.text_channels[0]
                await channel.send(message)
            except:
                failed.append(guild.name)
        if failed:
            guilds = ", ".join(failed)
            await ctx.send(f"Failed to send message to the following guilds: {guilds}")

    @commands.group(name="log", aliases=["logs"])
    async def log(self, ctx: commands.Context) -> None:
        if not ctx.invoked_subcommand:
            raise CommandError("A subcommand is required!")

    def _get_log_dir(self) -> Path:
        if os.environ.get("VJEMMIE_DIR"): # Use walrus operator? somewhat disgusting
            vjemmie_dir = Path(os.environ.get("VJEMMIE_DIR", "")) # default value to please mypy
        else:
            vjemmie_dir = Path.home() / "vjemmie"
        
        if not vjemmie_dir.exists():
            raise CommandError(
                "Unable to locate vjemmie directory. "
                "Either set environment variable 'VJEMMIE_DIR' to the path of the bot's directory. "
                f"Or install vjemmie at {Path.home() / 'vjemmie'}"
            )

        log_dir = vjemmie_dir / "logs"
        # Check if log dir exists
        if not log_dir.exists():
            raise CommandError("Unable to locate log directory!")
        
        return log_dir

    def get_log_file(self, log_name: Optional[str]) -> Path:
        if not log_name:
            log_name = "vjemmie.log" # Need to specify environ vars
        
        log_dir = self._get_log_dir()
        
        # Check if log file exists
        logfile = log_dir / log_name
        if not logfile.exists():
            raise CommandError(f"`{str(logfile)}` does not exist!")
        
        return logfile    

    @log.command(name="get")
    async def post_log(self, ctx: commands.Context, log_name: str=None, encoding: str="utf-8") -> None:
        """Print a log file in its entirety."""
        log = self.get_log_file(log_name)
        await self.read_send_file(ctx, log, encoding=encoding)

    @log.command(name="tail")
    async def post_log_tail(self, ctx: commands.Context, log_name: str=None, lines: int=5, encoding="utf8") -> None:
        """Print last N lines of a log file."""
        log = self.get_log_file(log_name)
        
        async with AIOFile(log, "r", encoding=encoding) as f:
            _contents = (await f.read()).splitlines()[-lines:]
        contents = "\n".join(_contents)
        
        await self.send_text_message(contents, ctx)


    @log.command(name="list")
    async def list_log_files(self, ctx: commands.Context) -> None:
        log_dir = self._get_log_dir()
        files = "\n".join(
            str(f) for f in log_dir.iterdir()
        )
        await self.send_text_message(files, ctx)

    @commands.command(name="blacklist")
    @admins_only()
    async def blacklist(self, ctx: commands.Context, member: commands.MemberConverter=None, command: str=None, *, output: bool=True) -> None:
        if member: # Proceed if discord.commands.MemberConverter returns a member
            blacklist = load_blacklist() # Get most recent version of blacklist
            if member.id not in blacklist:
                blacklist.append(member.id)
                save_blacklist(blacklist) # Save new version of blacklist
            if output:
                await ctx.send(await self.make_codeblock(f"Added {member.name} to blacklist"))
        else:
            show_cmd = self.bot.get_command("show")
            await ctx.invoke(show_cmd, "blacklist")

    @commands.command(name="show")
    @admins_only()
    async def show_xlist(self, ctx: commands.Context, list_name: str) -> None:
        list_name = list_name.lower()
        out_list = None
        if list_name in ["black", "blacklist", "blvck"]:
            out_list = load_blacklist()
        # TODO: Add other lists (commands, cogs, etc.)
        if out_list:
            out_list = [self.bot.get_user(user_id).name for user_id in out_list]
            out_msg = await self.format_markdown_list(out_list)
        else:
            out_msg = await self.make_codeblock("Blacklist is empty")
        await ctx.send(out_msg)

    @commands.command(name="unblacklist", aliases=["remove_blacklist", "rblacklist"])
    @admins_only()
    async def unblacklist(self, ctx: commands.Context, member: commands.MemberConverter=None, command: str=None, *, output: bool=True) -> None:
        if member: # Proceed if discord.commands.MemberConverter returns a member
            blacklist = load_blacklist() # Get most recent version of blacklist
            if member.id in blacklist:
                blacklist.remove(member.id)
                save_blacklist(blacklist) # Save new version of blacklist
                out_msg = f"Removed {member.name} from blacklist"
        else:
            await ctx.send("Do you want to clear the entire blacklist?")
            def pred(m) -> bool:
                return m.author == ctx.message.author and m.channel == ctx.message.channel
            try:
                reply = await self.bot.wait_for("message", check=pred, timeout=10.0)
            except asyncio.TimeoutError:
                await ctx.send("No reply from user")
            else:
                r = reply.content.lower()
                if r in YES_ARGS:
                    save_blacklist([]) # Clear blacklist
                    out_msg = "Cleared blacklist"
                else:
                    out_msg = "Blacklist unchanged"
        if output:
            await ctx.send(await self.make_codeblock(out_msg))

    @commands.command(name="timeout")
    @admins_only()
    async def timeout(self, ctx: commands.Context, member: commands.MemberConverter, duration_min: Union[int, float]=30) -> None:
        sleep_duration_sec = 60 * duration_min
        await ctx.invoke(self.blacklist, member, output=False)
        await ctx.send(f"Timing out {member.name} for {sleep_duration_sec} seconds.")
        await asyncio.sleep(sleep_duration_sec)
        await ctx.invoke(self.unblacklist, member, output=False)
        await ctx.send(f"Timeout ended for {member.name}")

    @commands.command(name="delete_messages", aliases=["dlt"])
    @admins_only()
    async def delete_messages(self,
                              ctx: commands.Context,
                              member: str=None,
                              content: Optional[str]=None) -> None:

        after = datetime.now() - timedelta(hours=2)

        try:
            m = await commands.MemberConverter().convert(ctx, member)
        except:
            m = None

        n = 0
        async for msg in ctx.message.channel.history(limit=250, after=after):
            if content and content in msg.content and msg.content != ctx.message.content:
                await msg.delete()
                n += 1
            if m and m.name == msg.author.name:
                await msg.delete()
                n += 1
        s = "s" if n>1 else ""
        await ctx.send(f"```\nDeleted {n} message{s}```")

    @commands.command(name="react")
    @admins_only()
    async def react_to_message(self,
                               ctx: commands.Context,
                               message_id: int,
                               emoji: str,
                               channel_id: int=None) -> None:
        """Adds emoji reaction to a specific message posted in
        `ctx.channel` or in a specific channel."""
        # Get channel
        channel = self.bot.get_channel(channel_id) if channel_id else ctx.channel

        # Iterate through 500 most recent messages
        async for msg in channel.history(limit=500):
            if msg.id == message_id:
                return await msg.add_reaction(emoji)
        else:
            return await ctx.send(
                # Should improve wording of this message
                f"No message with id {message_id} in the most recent 500 messages sent."
                )

    @commands.group(name="trusted", enabled=False)
    async def trusted(self, ctx: commands.Context) -> None:
        if not ctx.guild:
            raise CommandError("This action cannot be performed in a DM channel.")

        if not ctx.invoked_subcommand:
            return

    @trusted.command(name="add")
    @admins_only()
    async def trusted_add(self, ctx: commands.Context, member: commands.MemberConverter) -> None:
        add_trusted_member(ctx.guild.id, member.id)
        await ctx.send(f"Added {member.name} to {ctx.guild.name}'s trusted members!")

    @trusted.command(name="addrole", alias=["addrank", "add_role", "add_rank"])
    @admins_only()
    async def trusted_add_role(self, ctx: commands.Context, role: commands.RoleConverter) -> None:
        add_trusted_role(ctx.guild.id, role.id)
        await ctx.send(f"Added {role.name} to {ctx.guild.name}'s trusted roles!")

    @trusted.command(name="remove", aliases=["delete", "rm"])
    @admins_only()
    async def trusted_remove(self, ctx: commands.Context, member: commands.MemberConverter) -> None:
        try:
            remove_trusted_member(ctx.guild.id, member.id)
        except ValueError:
            await ctx.send(f"{member.name} is not a part of this guild's trusted members!")
        else:
            await ctx.send(f"Removed **`{member.name}`** from {ctx.guild.name}'s trusted members!")

    @trusted.command(name="removerole", aliases=["remove_role", "removerank", "remove_rank", "rmrole"])
    @admins_only()
    async def trusted_remove_role(self, ctx: commands.Context, role: commands.RoleConverter) -> None:
        try:
            remove_trusted_role(ctx.guild.id, role.id)
        except ValueError:
            await ctx.send(f"{role.name} is not a part of this guild's trusted roles!")
        else:
            await ctx.send(f"Removed **`{role.name}`** from {ctx.guild.name}'s trusted roles!")

    #@trusted.command(name="list", aliases=["show"])
    #@admins_only()
    @trusted.group(name="list", aliases=["show"])
    async def trusted_show(self, ctx: commands.Context) -> None:
        if not ctx.invoked_subcommand:
            #self.bot.get_command(ctx.invoked_with)
            cmds = "/".join([cmd.name for cmd in ctx.command.commands])
            return await ctx.send("No subcommand invoked! \n"
                f"**Usage:** `{ctx.command.qualified_name} <{cmds}>`")

    @trusted_show.command(name="members", aliases=["users"])
    async def trusted_show_users(self, ctx: commands.Context) -> None:
        await self._show_trusted(ctx, category="members", content=self.fmt_trusted_members)

    @trusted_show.command(name="roles")
    async def trusted_show_roles(self, ctx: commands.Context) -> None:
        await self._show_trusted(ctx, category="roles", content=self.fmt_trusted_roles)

    async def _show_trusted(self, ctx: commands.Context, category: str, content: Awaitable) -> None:
        c = await content(ctx)
        
        if not content:
            return await ctx.send(f"No trusted {category} added.")

        await self.send_embed_message(
            ctx,
            title=f"{ctx.guild.name} Trusted {category.capitalize()}",
            description=c,
            color=self.get_bot_color(ctx))

    async def fmt_trusted_members(self, ctx: commands.Context) -> str:
        members = get_trusted_members(ctx.guild.id)

        # drop users whose ID can't be identified
        users = list(filter(None.__ne__, [self.bot.get_user(member) for member in members]))
        u = "\n".join([f"{u.name}`#{u.discriminator}`" for u in users])

        return u

    async def fmt_trusted_roles(self, ctx: commands.Context) -> str:
        roles = get_trusted_roles(ctx.guild.id)

        roles = list(filter(None.__ne__, [await commands.RoleConverter().convert(ctx, str(role)) for role in roles]))
        r = "\n".join([role.name for role in roles])

        return r

    @tasks.loop(seconds=86400.0)
    async def system_diagnostics_loop(self) -> None:
        # do status loop
        coros = [
            self.check_disk_usage,
            self.check_memory_usage,
            self.check_cpu_usage
        ]

        fields = list(filter(None.__ne__, [await coro() for coro in coros]))
        if not fields:
            return
            fields = [EmbedField(
                name="❌ **Disk Usage**", 
                value="Disk is full! Downloads are disabled until at least 10% disk space is available."
            )]


        embed = await self.get_embed(
            footer=False, 
            title=f"{self.bot.user.name} Diagnostics Report", 
            description=" ",
            fields=fields,
            #author=self.bot.user.name,
            #author_icon=self.bot.user.avatar_url
        )
        owner = self.bot.get_user(OWNER_ID)
        if not owner:
            eprint(f"Unable to find a user with ID {OWNER_ID}")
            return
        
        # Get DM channel or create one
        if owner.dm_channel:
            dm_channel = owner.dm_channel
        else:
            dm_channel = await owner.create_dm()

        await dm_channel.send(embed=embed)

    async def check_disk_usage(self) -> Optional[EmbedField]:
        usage = psutil.disk_usage(Path(__file__).root)
        if usage.percent > 99.0:
            #config.DOWNLOADS_ALLOWED = False
            # TODO: Fix
            return EmbedField(
                name="❌ **Disk Usage**", 
                value="Disk is full! Downloads are disabled until at least 10% disk space is available."
            )
        elif usage.percent > 90.0:
            return EmbedField(
                name="⚠️ **Disk Usage**", 
                value="Disk usage exceeds 90%! Free up disk space or consider disabling downloads."
            )
        
    async def check_memory_usage(self) -> Optional[EmbedField]:
        usage = psutil.virtual_memory()
        if usage.percent > 90.0:
            return EmbedField(
                name="⚠️ **Memory Usage**", 
                value="Less than 10% free memory! Consider upgrading hosting solution or stopping unnecessary processes."
            )
        
    async def check_cpu_usage(self) -> Optional[EmbedField]:
        if sys.platform == "windows":
            from psutil._pswindows import \
                _loadavg_inititialized  # yes, spelling error in psutil LOL

            # psutil.getloadavg() needs to be "primed" on Windows for minimum 5 seconds
            # https://psutil.readthedocs.io/en/latest/#psutil.getloadavg
            #
            # We don't really need to check _loadavg_initialized, but we can
            # just do it here to avoid sleeping for 5.5 seconds every time
            if not _loadavg_inititialized: 
                psutil.getloadavg() 
                await asyncio.sleep(5.5)
        
        usage = [x / psutil.cpu_count() * 100 for x in psutil.getloadavg()]

        # NOTE: if any(core > 99.0 for core in usage) ?
        if usage[0] > 90.0:
            return EmbedField(
                name="⚠️ **CPU Usage**", 
                value="Average CPU usage is 90%! Consider upgrading hosting solution or stopping unnecessary processes."
            )
