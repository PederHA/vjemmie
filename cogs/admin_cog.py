import asyncio
import os
from pathlib import Path
from collections import namedtuple
from datetime import datetime, timedelta
from functools import partial
from typing import Optional, Union, Awaitable

import discord
from discord.ext import commands

from cogs.base_cog import BaseCog, EmbedField
from config import TRUSTED_DIR, TRUSTED_PATH, YES_ARGS
from utils.access_control import (Categories, add_trusted_member,
                                  add_trusted_role, get_trusted_members,
                                  get_trusted_roles, remove_trusted_member,
                                  remove_trusted_role)
from utils.checks import admins_only, load_blacklist, save_blacklist
from utils.exceptions import CommandError

Activity = namedtuple("Activity", "text callable is_coro", defaults=["", None, False])

class AdminCog(BaseCog):
    DISABLE_HELP = False
    ACTIVITY_ROTATION = True

    FILES = [TRUSTED_PATH]

    """Admin commands for administering guild-related bot functionality."""
    @commands.Cog.listener()
    async def on_ready(self) -> None:
        """Sets activity and prints a message when cog is instantiated 
        and added to the bot.
        """
        print("Bot logged in")
        await self.run_activity_rotation()

    async def run_activity_rotation(self) -> None:
        p = self.bot.command_prefix

        acitivities = [
            Activity(f"{p}about"),
            Activity(f"{p}help"),
            Activity(f"{p}commands"),
            Activity("Uptime: ", partial(self.bot.get_cog("StatsCog").get_bot_uptime, type=str))
        ]

        while self.ACTIVITY_ROTATION:
            for ac in acitivities:
                if not ac.text and not ac.callable:
                    continue # Skip if activity has no text or callable
                if ac.callable:
                    if ac.is_coro:
                        r = await ac.callable()
                    else:
                        r = ac.callable()
                    await self._change_activity(f"{ac.text}{r}")
                else:
                    await self._change_activity(ac.text)
                await asyncio.sleep(30)

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild) -> None:
        """Called when bot joins a guild."""
        await self.send_log(f"Joined guild {guild.name}", channel_id=self.GUILD_HISTORY_CHANNEL)

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild) -> None:
        """Called when bot leaves a guild."""
        await self.send_log(f"Left guild {guild.name}", channel_id=self.GUILD_HISTORY_CHANNEL)

    async def _change_activity(self, activity_name: str) -> None:
        activity = discord.Game(activity_name)
        await self.bot.change_presence(activity=activity)

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
            await self._change_activity(activity_name)
        elif not activity_name and not self.ACTIVITY_ROTATION:
            # Run activity rotation
            self.ACTIVITY_ROTATION = True
            await self.run_activity_rotation()
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
    async def sendtoall(self, ctx: commands.Context, *msg) -> None:
        """
        Attempts to send text message to every server the bot
        is a member of.
        
        Parameters
        ----------
        ctx : `commands.Context`
            Discord context
        msg: `tuple`
            String to send.
        """
        msg = " ".join(msg)
        guilds = self.bot.guilds
        for guild in guilds:
            channel = guild.text_channels[0]
            try:
                await channel.send(message)
            except:
                # CBA spamming log channel with every message attempt
                print(f"Failed to send message to guild {guild.name}")

    @commands.group(name="log", aliases=["logs"])
    async def log(self, ctx: commands.Context) -> None:
        if not ctx.invoked_subcommand:
            raise CommandError("A subcommand is required!")

    def get_log_dir(self) -> None:
        try:
            immortal_dir = os.environ["IMMORTAL_SDIR"]
        except KeyError:
            raise CommandError("Immortal SDIR environment variable is not set!")

        # Check if log dir exists
        log_dir = Path(immortal_dir) / "logs"
        if not log_dir.exists():
            raise CommandError("Unable to locate log directory!")
        
        return log_dir

    @log.command(name="get")
    async def post_log(self, ctx: commands.Context, log_name: str=None, encoding: str="utf-8") -> None:
        log_dir = self.get_log_dir()
        
        # Check if log file exists
        log = log_dir / log_name
        if not log.exists():
            raise CommandError(f"`{str(log)}` does not exist!")
        
        await self.read_send_file(ctx, log, encoding=encoding)

    @log.command(name="list")
    async def list_log_files(self, ctx: commands.Context) -> None:
        log_dir = self.get_log_dir()
        
        files = "\n".join(list(log_dir.iterdir()))

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
            member = await commands.MemberConverter().convert(ctx, member)
        except:
            member = None

        n = 0
        async for msg in ctx.message.channel.history(limit=250, after=after):
            if content and content in msg.content and msg.content != ctx.message.content:
                await msg.delete()
                n += 1
            if member and member.name == msg.author.name:
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
                f"No message with id {message_id} found or it is too old."
                )

    @commands.group(name="trusted")
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
        content = await content(ctx)
        
        if not content:
            return await ctx.send(f"No trusted {category} added.")

        await self.send_embed_message(
            ctx,
            title=f"{ctx.guild.name} Trusted {category.capitalize()}",
            description=content,
            color=self.get_bot_color(ctx))

    async def fmt_trusted_members(self, ctx: commands.Context) -> str:
        members = get_trusted_members(ctx.guild.id)

        # drop users whose ID can't be identified
        users = list(filter(None.__ne__, [self.bot.get_user(member) for member in members]))
        users = "\n".join([f"{u.name}`#{u.discriminator}`" for u in users])

        return users

    async def fmt_trusted_roles(self, ctx: commands.Context) -> str:
        roles = get_trusted_roles(ctx.guild.id)

        roles = list(filter(None.__ne__, [await commands.RoleConverter().convert(ctx, str(role)) for role in roles]))
        roles = "\n".join([role.name for role in roles])

        return roles
