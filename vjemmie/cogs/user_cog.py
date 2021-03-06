import sys
from collections import namedtuple
from contextlib import suppress
from random import randint
from typing import List

import discord
import psutil
from discord.ext import commands

from ..config import AUTHOR_MENTION, YES_ARGS
from ..utils.converters import BoolConverter
from ..utils.exceptions import CategoryError, CogError, CommandError
from ..utils.time import format_time
from .base_cog import BaseCog, EmbedField


CommandCooldown = namedtuple("CommandCooldown", ["command", "cooldown"])

class UserCog(BaseCog):
    """Help commands."""

    def __init__(self, bot: commands.Bot):
        super().__init__(bot)
        self.bot.remove_command('help')

    @commands.command(name="help", aliases=["Help", "hlep", "?", "pls"], usage="<command/category>")
    async def help_(self, ctx: commands.Context, cmd_or_category: str=None, advanced: BoolConverter(["advanced"])=False) -> None:
        """Alias for both `command` and `category`. Prioritizes commands.
        
        If a command and a category have the same name, distinguish between them by
        typing the category's name with an upper case letter:

        `!help reddit` -> The reddit command
        `!help Reddit` -> The reddit category 
        """
        if not cmd_or_category:
            return await ctx.send(
                "Specify a command or category to get help for!\n"
                f"Usage: `{self.bot.command_prefix}help <command/category> [advanced]`\n"
                f"`{self.bot.command_prefix}commands` to get a list of commands\n"
                f"`{self.bot.command_prefix}categories` to get a list of categories."
                )
        
        # Check if cmd_or_category is a command
        try:
            await ctx.invoke(self.help_command, cmd_or_category, advanced)
        except CommandError:
            pass
        else:
            return

        # Check if cmd_or_category is a category if previous attempt failed
        try:
            await ctx.invoke(self.help_category, cmd_or_category, advanced)
        except CommandError:
            raise CommandError(f"No command or category named `{cmd_or_category}`")

    @commands.command(name="category")
    async def help_category(self, ctx: commands.Context, cog_name: str=None, advanced: BoolConverter(["advanced"])=False):
        """Sends information about a specific category's commands"""
        # We refer to cogs as categories to users 
        for cog in await self.get_cogs():
            if cog_name.lower() == cog.cog_name.lower():
                cmds = await cog.get_invokable_commands(ctx)
                if not cmds:
                    raise CommandError("Category has no associated commands!")
                return await cog.send_cog_commands(ctx, advanced)
        
        # If loop does not raise error or return, it means cog does not exist.
        raise CommandError(f"No such category **{cog_name}**.")
    
    @commands.command(name="categories")
    async def help_categories(self, ctx: commands.Context) -> None:
        cogs = await self.get_cogs()
        for idx, cog in enumerate(cogs):
            if not await cog.get_invokable_commands(ctx) or not cog.__doc__:
                cogs.pop(idx)
        
        description = "\n".join([f"{cog.EMOJI} **{cog.cog_name}**: {cog.__doc__}\n" for cog in cogs])
        await self.send_embed_message(ctx, title="Categories", description=description)

        # Send !help usage instructions
        await ctx.send(f"Type `{self.bot.command_prefix}help <category> [advanced]` for a specific category.\n"
                        f"Or type `{self.bot.command_prefix}commands` to show all available commands.")

    @commands.command(name="command", aliases=["cmd"])
    async def help_command(self, ctx: commands.Context, command: str, advanced: bool) -> None:
        cmd = self.bot.get_command(command)

        if not cmd:
            raise CommandError(f"`{self.bot.command_prefix}{command}` not found!")

        _cmd_name = f"{self.bot.command_prefix}{cmd.qualified_name}"

        # Embed title
        title = f"**`{_cmd_name}`**"

        sig = (cmd.usage or cmd.signature or '') if advanced else ''
        if advanced and sig: # really no elegant way to do this
            sig = f" {sig}"

        # Embed description
        description = [
            f"_{cmd.help_doc}_\n",
            f"**Category:** {cmd.cog.EMOJI}{cmd.cog.cog_name}",
            f"**Usage:** `{_cmd_name}{sig}`"
        ]

        # Include subcommands if they exist
        if isinstance(cmd, commands.Group):
            subcommands = "\n**Subcommands:\n** " + "\n".join([
                f"`{_cmd.name.ljust(20, self.EMBED_FILL_CHAR)}:` {_cmd.short_doc}"
                for _cmd in cmd.commands
            ])
            description.append(subcommands)

        # Number of times the command has been used in the guild
        description.append(f"**Times used:** {self.get_command_usage(ctx, command)}")

        # Top user of the command
        top_users = self.bot.get_cog("StatsCog").get_top_command_users(ctx.guild.id, command, limit=10)
        if top_users:
            # Iterate until a valid user is found (our top user might have left the server)
            for user_id, n_used in top_users.items():
                user = self.bot.get_user(user_id)
                if user:
                    description.append(f"**Top User:** {user.mention} ({n_used})")
                    break
        
        description = "\n".join(description)

        await self.send_embed_message(ctx, title=title, description=description)

    def get_command_usage(self, ctx, command: str) -> int:
        stats_cog = self.bot.get_cog("StatsCog") 
        return stats_cog.get_command_usage(ctx.guild.id, command)

    @commands.command(name="commands")
    async def show_commands(self,
                            ctx:commands.Context,
                            advanced: BoolConverter(["advanced", "y", "args"])=False
                            ) -> None:
        """Display all bot commands."""
        l = []
        for cog in await self.get_cogs():
            # Ignore cogs returning no commands due to failed checks or lack of commands
            with suppress(CommandError):
                #cmds = await cog._get_cog_commands(ctx, advanced, rtn=True)
                cmds = await cog._get_cog_commands(ctx, advanced)
                l.append(f"{cog.EMOJI} **{cog.cog_name}**\n_{cog.__doc__}_\n{cmds}\n")

        if not l:
            raise CommandError("No commands are available!")

        out = "\n".join(l)
        if advanced:
            # Add command signature legend to top of embed if advanced output is enabled
            out = self.SIGNATURE_HELP + out

        await self.send_embed_message(ctx, "Commands", out, color="red")


    @commands.command(name="invite", aliases=["get_invite"])
    async def invitelink(self, ctx: commands.Context) -> None:
        """Get discord bot invite URL"""
        base_url = "https://discordapp.com/api/oauth2/authorize?client_id={id}&scope=bot&permissions={permissions}"

        levels = {
            "Minimal": 70642752,
            "Standard (Recommended)": 133557312,
            "Admin": 2146958839
        }

        out_str = "\n".join(
            [
            f"[**{level}**]({base_url.format(id=self.bot.user.id, permissions=permissions)})"
            for level, permissions in levels.items()
            ]
        )

        embed = await self.get_embed(ctx,
                                     author=f"Invite {self.bot.user.name}",
                                     author_icon="https://discordapp.com/assets/2c21aeda16de354ba5334551a883b481.png",
                                     description=out_str,
                                     color="blurple"
                                     )
        return await ctx.send(embed=embed)


    @commands.command(name="about", aliases=["info"])
    async def about(self, ctx: commands.Context) -> None:
        """General bot information."""
        # Memory
        mem = psutil.virtual_memory()
        mem_total_mb = round(mem.total / 1000000)
        mem_used_mb = round(mem.used / 1000000)
        #mem_graphic = f"[{'l'*round(mem.percent/10)}{'_'*round((100-mem.percent)/10)}]"

        # Soundboard
        sound_cog = self.bot.get_cog("SoundCog")
        try:
            n_soundfiles = len(sound_cog.sound_list)
        except:
            n_soundfiles = 0

        p = self.bot.command_prefix
        fields = [
            EmbedField(name="Owner", value=AUTHOR_MENTION),
            EmbedField(name="Running on", value=f"<:python:570331647933677590> Python {sys.version.split(' ')[0]}"),
            EmbedField(name="Command categories", value=len(await self.get_cogs())),
            EmbedField(name="Useful commands", value=f"`{p}help`, `{p}commands`, `{p}categories`, `{p}changelog`"),
            EmbedField(name="Soundboard files", value=f"{n_soundfiles}"),
            EmbedField(name="Memory usage", value=f"{mem_used_mb} / {mem_total_mb} MB"),
            EmbedField(name="CPU Usage", value=f"{psutil.cpu_percent()}%"),
            EmbedField(name="Uptime", value=self.bot.get_cog("StatsCog").get_bot_uptime(type=str)),
        ]

        embed = await self.get_embed(ctx,
                                     author=self.bot.user.name,
                                     author_icon=self.bot.user.avatar_url._url,
                                     description="Top secret bot running on the Tiger Mafia mainframe.",
                                     fields=fields)

        await ctx.send(embed=embed)

    @commands.command(name="cooldowns", aliases=["coolies"])
    async def get_cooldowns(self, ctx: commands.Context) -> None:
        """Displays commands you are on cooldown for."""
        # Iterating through command cooldowns blocks, so we run it in a thread
        # (the overhead incurred from this probably isn't worth it for a small bot like VJ Emmie)
        cooldowns = await self.bot.loop.run_in_executor(None, self._get_command_cooldowns, ctx)

        if not cooldowns:
            return await ctx.send("You are not on cooldown for any commands!")

        # Format output message
        longest_name = max([len(cmd.name) for cmd, _ in cooldowns])
        fchar = self.EMBED_FILL_CHAR # to make expression more readable
        desc = "\n".join([
            f"`{cmd.name.ljust(longest_name, fchar)}:`{fchar*3}{format_time(cd)}" 
            for cmd, cd in cooldowns
        ])

        await self.send_embed_message(
            ctx, 
            title=f"Cooldowns for {ctx.message.author.name}",
            description=desc, 
            thumbnail_url=ctx.message.author.avatar_url,
        )

    def _get_command_cooldowns(self, ctx: commands.Context) -> List[CommandCooldown]:
        cooldowns: List[CommandCooldown] = []
        for command in self.bot.commands:
            cd = command.get_cooldown_retry_after(ctx)
            if cd:
                cooldowns.append(
                    CommandCooldown(
                        command=command,
                        cooldown=cd,
                    )
                )
        return cooldowns
