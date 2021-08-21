import hashlib
import io
import os.path
import traceback
from asyncio import TimeoutError
from collections import namedtuple
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Iterable, List, Mapping, Optional, Tuple, Union
from urllib.parse import urlparse, urlsplit

import aiohttp
import discord
import psutil
from aiofile import AIOFile
from discord import Embed
from discord.ext import commands
from httpcore._exceptions import ConnectError, ConnectTimeout
from loguru import logger
from prawcore.exceptions import Forbidden as PrawForbidden
from youtube_dl import DownloadError

from ..config import config
from ..utils.exceptions import (
    VJEMMIE_EXCEPTIONS,
    BotPermissionError,
    CategoryError,
    CommandError,
    FileSizeError,
    FileTypeError,
    InvalidVoiceChannel,
    NoContextException,
)
from ..utils.experimental import get_ctx
from ..utils.http import get
from ..utils.time import format_time
from ..utils.users import get_user
from ..utils.voting import NotEnoughVotes

md_formats = [
    "asciidoc",
    "autohotkey",
    "bash",
    "coffeescript",
    "cpp",
    "cs",
    "css",
    "diff",
    "fix",
    "glsl",
    "ini",
    "json",
    "md",
    "ml",
    "prolog",
    "py",
    "tex",
    "xl",
    "xml",
]

EmbedField = namedtuple("EmbedField", "name value inline", defaults=[True])

# Exception types

# Show original exception message for these exception types, otherwise show "Unknown error"
SHOW_ERROR = [
    commands.errors.MissingRequiredArgument,
    MemoryError,
    discord.DiscordException,
    DownloadError,  # youtube-dl
    TypeError,
    ConnectError,  # httpx
    ConnectTimeout,  # httpx
    ConnectionError,
]
SHOW_ERROR += VJEMMIE_EXCEPTIONS

# Don't log traceback of these exception types
IGNORE_TRACEBACK = [
    BotPermissionError,
    CategoryError,
    InvalidVoiceChannel,
    commands.errors.MissingRequiredArgument,
    PrawForbidden,
    CommandError,
    DownloadError,
    commands.errors.DisabledCommand,
    NotEnoughVotes,
]

IGNORE_EXCEPTION = [TimeoutError]


class BaseCog(commands.Cog):
    """Base Cog from which all other cogs are subclassed."""

    # Cogs to ignore when creating !help commands
    DISABLE_HELP = False

    # Valid image extensions to post to a Discord channel
    IMAGE_EXTENSIONS = [".jpeg", ".jpg", ".png", ".gif", ".webp"]

    # Embed Options
    CHAR_LIMIT = 1800
    EMBED_CHAR_LIMIT = 1000
    EMBED_FILL_CHAR = "\xa0"

    # Style info for help categories
    EMOJI = ":question:"

    # Directories and files necessary for cog
    DIRS: List[str] = []
    FILES: List[str] = []

    # Help strings
    SIGNATURE_HELP = "**Signature Legend**\n●`<arg>` is a required argument\n●`[arg]` is an optional argument\n\n"

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.setup()

    def setup(self, default_factory: Callable = dict) -> None:
        """Creates files and folders required for the cog."""
        # Create required directories
        for directory in self.DIRS:
            p = Path(directory)
            if not p.exists():
                p.mkdir(parents=True, exist_ok=True)

        # Create required files
        for _file in self.FILES:
            p = Path(_file)
            p.parent.mkdir(parents=True, exist_ok=True)
            if not p.exists():
                p.touch()
                if p.suffix == ".json":
                    p.write_text(f"{default_factory()}")

    # Override default exception handler
    async def cog_command_error(
        self, ctx: commands.Context, error: Exception, *bugged_params
    ) -> None:
        """Handles exceptions raised by commands defined in the cog.

        Parameters
        ----------
        ctx : commands.Context
            Discord Context object
        error : Exception
            Exception that was raised
        """
        # This might have been fixed in a recent version of Discord.py
        if bugged_params:
            ctx = error
            error = bugged_params[0]

        # Check if error stems from lack of privileges
        if isinstance(error, commands.CheckFailure):
            # only post this catch-all message for general check failures
            # Subclassed check failures should be handled by their own coroutine
            if issubclass(error.__class__, commands.CheckFailure):
                return
            return await ctx.send("Insufficient privileges to execute command!")

        # Ignore cooldown exceptions
        if isinstance(error, commands.CommandOnCooldown):
            return await ctx.send(
                f"You are on cooldown for **`{ctx.prefix}{ctx.invoked_with}`**. "
                f"Try again in {format_time(error.retry_after)}"
            )

        # Default error handler
        return await self._handle_error(ctx, error)

    @property
    def cog_name(self) -> str:
        cog_name = self.__class__.__name__
        return cog_name if not cog_name.endswith("Cog") else cog_name[:-3]

    @property
    def MAX_DL_SIZE_FMT(self) -> str:
        size_mb = config.MAX_DL_SIZE / 1_000_000
        return f"{size_mb} MB"

    @property
    def BOT_COLOR(self) -> discord.Color:
        """experimental"""
        default = discord.Color(0x000000)

        try:
            ctx = get_ctx()
        except NoContextException:
            return default

        bot_member = ctx.guild.get_member(self.bot.user.id)

        if not bot_member:
            return default
        else:
            return bot_member.color

    def get_bot_color(self, ctx) -> discord.Color:
        """Safe, but boring, implementation of `BOT_COLOR`."""
        bot_member = ctx.guild.get_member(self.bot.user.id)
        return bot_member.color

    async def format_markdown_list(
        self,
        items: Iterable[str],
        *,
        formatting: str = "",
        title: str = None,
        enum: bool = False,
    ) -> str:
        """
        Creates a multi-line codeblock in markdown formatting
        listing items in iterable `items` on separate lines.

        NOTE
        ----
        This method is more or less deprecated in favor of methods
        using discord.Embed objects.

        Parameters
        ----------
        items : `Iterable`
            Iterable of strings to format
        title : `str`, optional
            Description of items in iterable. Default: None
        enum : `bool`, optional
            Adds index number next to each item listing. Default: False

        Returns
        -------
        output : `str`
            Markdown formatted code block of items in iterable, 1 item per line.

        Example
        -------
        >>>format_markdown_list(["foo", "bar", "baz"], "Title")
        '```
        Title:

        1. foo
        2. bar
        3. baz
        ```'
        """
        if formatting not in md_formats:
            formatting = ""

        _out = [f"```{formatting}"]

        if title:
            _out.append(f"{title}:\n")

        idx = ""
        for i, item in enumerate(items, 1):
            if enum:
                idx = f"{i}. "
            _out.append(f"{idx}{item}")
        else:
            _out.append("```")
        return "\n".join(_out)

    async def make_codeblock(self, content: str, md_format: str = None) -> str:
        md_format = md_format if md_format in md_formats else ""
        return f"```{md_format}\n{content}\n```"

    async def get_discord_color(self, color: Union[str, int]) -> discord.Color:
        """Returns a discord.Color object corresponding to a color specified
        by name as `str` or as a hexadecimal `int`.

        Parameters
        ----------
        color : `Union[str, int]`
            Example:
            >>> get_discord_color("red")
            >>> get_discord_color(0x4a998a)

        Raises
        ------
        discord.DiscordException
            If discord.Color has no classmethod with name `color`
        discord.DiscordException
            If type of argument `color` is neither `int` nor `str`

        Returns
        -------
        discord.Color
            A discord.Color object initialized with the desired color
        """
        # Parse str arg
        if isinstance(color, str):
            try:
                # discord.Color has classmethods for several basic colors. Check src!
                color_classmethod = getattr(discord.Color, color)
            except:
                raise CommandError(f"Could not interpret {color}")
            else:
                return color_classmethod()
        # Parse int arg
        elif isinstance(color, int):
            return discord.Color(color)
        else:
            raise CommandError("Argument must be type 'str' or type 'int'")

    async def get_embed(
        self,
        ctx: commands.Context = None,
        *,
        author: Optional[str] = None,
        author_url: str = Embed.Empty,
        author_icon: str = Embed.Empty,
        title: str = Embed.Empty,
        description: str = Embed.Empty,
        fields: Optional[List[EmbedField]] = None,
        image_url: Optional[str] = None,
        thumbnail_url: Optional[str] = None,
        color: Optional[Union[str, int, discord.Color]] = None,
        footer: bool = True,
        timestamp: bool = True,
        inline: Optional[bool] = None,
    ) -> discord.Embed:
        """Constructs a discord.Embed object.

        Parameters
        ----------
        ctx : `commands.Context`, optional
            Discord Context. A required parameter if footer==True.
        author : `str`, optional
            Author name displayed on topmost line of embed.
            Intended for name of embed author, but can be anything.
        author_url: `str`, optional
            URL to make author name a clickable hyperlink.
            Author name is required!
        author_icon: `str`, optional
            URL to image.
            Image is displayed to the left of author's name.
            Author name is required!
        title : `str`, optional
            Title of embed.
            A single line of bolded text displayed below author name.
        description: `str`, optional
            Description field of embed, displayed below embed title.
        footer : `bool`, optional
            Display footer on embed in the format:
            <user avatar> <"requested by `user`"> <timestamp>
        fields : `list`, optional
            List of EmbedField objects. Each EmbedField is added as a
            new field to the embed via `embed.add_field`
        image_url : `str`, optional
            Image URL. TODO: Add more info
        color : `Union[str, int, None]`, optional
            Color of embed. Can be specified as str or int.
            See `BaseCog.get_discord_color` for info.
        timestamp : `bool`, optional
            Display timestamp on footer. Has no effect if
            param `footer=False`
        inline : `bool`, optional
            Display embed fields inline.
            Overrides whatever value is specified
            in list of EmbedField objects.

        Returns
        -------
        discord.Embed
            A Discord embed object that can be sent to a text channel
        """
        # Create embed object.
        # Timestamp must be specified on object instantiation
        opts = {"timestamp": datetime.now()} if timestamp else {}
        embed = discord.Embed(title=title, description=description, **opts)

        # Add author details
        if author:
            if await self.is_img_url(author_icon):
                icon_url = author_icon
            else:
                icon_url = Embed.Empty
            embed.set_author(name=author, url=author_url, icon_url=icon_url)
        # Add footer
        if footer and ctx:
            embed.set_footer(
                text=f"Requested by {ctx.message.author.name}",
                icon_url=ctx.message.author.avatar_url,
            )
        # TODO: footer==True fails silently if ctx==None, throw exception

        # Add embed fields
        if fields:
            for field in fields:
                # Make sure fields contains EmbedField objects
                if not isinstance(field, EmbedField):
                    raise discord.DiscordException(
                        f"'fields' must be a list of EmbedField objects!"
                    )

                # Use inline kw-only arg if given, otherwise use EmbedField's inline value
                il = inline if inline is not None else field.inline
                embed.add_field(name=field.name, value=field.value, inline=il)

        # Add image if URL is an image URL
        if image_url and await self.is_img_url(image_url):
            embed.set_image(url=image_url)

        # Add thumbnail if thumbnail URL is an image URL
        if thumbnail_url and await self.is_img_url(thumbnail_url):
            embed.set_thumbnail(url=thumbnail_url)

        # Add color to embed
        if color:
            if not isinstance(color, discord.Color):
                color = await self.get_discord_color(color)
            embed.color = color

        return embed

    async def get_usernames_in_voice_channel(
        self, ctx: commands.Context, nick: bool = False
    ) -> List[str]:
        """
        Returns list of discord usernames or nicks (EXCLUDING THE BOT ITSELF)
        in ctx.message.author's voice channel .
        """
        if not hasattr(ctx.message.author.voice, "channel"):
            raise CommandError("You are not connected to a voice channel.")
        return [
            member.nick if nick else member.name
            for member in ctx.message.author.voice.channel.members
            if member.id != self.bot.user.id
        ]

    async def get_members_in_voice_channel(
        self, ctx: commands.Context
    ) -> List[discord.Member]:
        """
        Returns list of `discord.Member` objects (EXCLUDING THE BOT ITSELF)
        from ctx.message.author's voice channel .
        """
        if not hasattr(ctx.message.author.voice, "channel"):
            raise CommandError("You are not connected to a voice channel.")
        return [
            member
            for member in ctx.message.author.voice.channel.members
            if member.id != self.bot.user.id
        ]

    async def find_user_in_voice_channel(
        self, ctx: commands.Context, name: str, nick: bool = True
    ) -> discord.Member:
        for member in ctx.message.author.voice.channel.members:
            if any(name == n for n in [member.nick, member.name]):
                return member

    async def send_log(self, msg: str, *, channel_id: int = None) -> None:
        """Sends log message to log channel

        Parameters
        ----------
        msg : `str`
            String to send as message to log channel
        """
        if not channel_id:
            channel_id = config.LOG_CHANNEL_ID

        try:
            await self.send_text_message(msg, channel_id=channel_id)
        except discord.Forbidden:
            logger.error(f"Insufficient permissions for channel {channel_id}.")
        except discord.HTTPException:
            logger.error(f"Failed to send message to channel {channel_id}.")

    async def log_error(self, ctx: commands.Context, error_msg: str = None) -> None:
        """Logs command exception to log channel

        Parameters
        ----------
        ctx : `commands.Context`
            Discord context, used to get message that caused
            command exception.
        error_msg : `str`
            Traceback returned by traceback.format_exc() from
            BaseCog._unknown_error()
        """
        if not error_msg:
            error_msg = traceback.format_exc()

        # Send message that caused error
        cause_of_error = (
            f"Message that caused error: {ctx.author.name}: {ctx.message.content}"
            if ctx
            else ""
        )

        # NOTE: logger.exception is unreadable to me, hence .error()
        logger.error(f"{error_msg}\n{cause_of_error}")

    async def warn_owner(self, message: str) -> None:
        channel = self.bot.get_channel(self.LOG_CHANNEL_ID)
        await channel.send(f"{config.AUTHOR_MENTION} {message}")

    async def _handle_error(self, ctx: commands.Context, error: Exception) -> None:
        # Show user original error message of these exception types
        if hasattr(error, "original"):
            error = error.original

        if any(isinstance(error, err) for err in IGNORE_EXCEPTION):
            return

        if any(isinstance(error, err) for err in SHOW_ERROR) and error.args:
            # Use original exception
            msg = error.args[0]
        else:
            msg = "An unknown error occured"

        # Log traceback in logging channel if exception class is not ignored
        log_error = not any(isinstance(error, err) for err in IGNORE_TRACEBACK)

        await self.send_error_msg(ctx, msg, log_error=log_error)

    async def send_error_msg(
        self, ctx: commands.Context, error_msg: str, *, log_error: bool = True
    ):
        """Method called when raised exception is not recognized
        by `BaseCog.cog_command_error()`

        Parameters
        ----------
        ctx : `commands.Context`
            Discord Context object
        error_msg : `str`
            Error message
        """

        # Display error to user
        await ctx.send(f"ERROR: {error_msg}")

        if log_error:
            # Get formatted traceback
            traceback_msg = traceback.format_exc()
            await self.log_error(
                ctx, traceback_msg
            )  # Send entire exception traceback to log channel

    async def get_aiohttp_session(self, ctx: commands.Context) -> aiohttp.ClientSession:
        """Retrieves per-guild aiohttp.ClientSession session object.
        Session is created for the guild if it has no active sessions.

        Parameters
        ----------
        ctx : `commands.Context`
            Discord context

        Raises
        ------
        `PermissionError`
            Raised if downloads are disabled in `config.py`

        Returns
        -------
        `aiohttp.ClientSession`
            aiohttp session for guild
        """

        # Check if downloads are enabled in config.
        if not config.DOWNLOADS_ALLOWED:
            raise BotPermissionError("Downloads are not allowed for this bot!")

        # Add bot attribute keeping track of aiohttp ClientSession objects
        if not hasattr(self.bot, "sessions"):
            self.bot.sessions = {}

        # Get client session for ctx.guild
        session = self.bot.sessions.get(ctx.guild.id)

        # Create persistent client session for guild if none exists
        if not session:
            session = aiohttp.ClientSession()
            self.bot.sessions[ctx.guild.id] = session

        return session

    async def download_from_url(self, ctx: commands.Context, url: str) -> io.BytesIO:
        """Downloads the contents of URL `url` and returns an `io.BytesIO` object.

        Returns
        -------
        `io.BytesIO`
            The downloaded contents of the URL
        """
        # Check if host responds
        try:
            resp = await get(url)
        except ConnectError:
            raise discord.DiscordException(
                "No response from destination host. Is the URL spelled correctly?"
            )
        except ConnectTimeout:
            raise discord.DiscordException(
                f"Failed to download from `{url}`. Connection timed out."
            )

        # Check content size
        content_length = int(resp.headers["Content-Length"])
        if content_length > config.MAX_DL_SIZE:
            raise FileSizeError(
                f"File exceeds maximum limit of {config.MAX_DL_SIZE_FMT}"
            )

        # Check available RAM
        # TODO: Should keep track of ALL downloads.
        # We might start several large downloads concurrently this way
        if content_length * 2 > psutil.virtual_memory().available:
            raise MemoryError(f"Not enough memory to download file!")

        # Download content
        data = await resp.aread()

        return io.BytesIO(data)

    async def rehost_image_to_discord(
        self, ctx: commands.Context, image_url: str
    ) -> discord.Message:
        """Downloads an image file from url `image_url` and uploads it to a
        Discord text channel.

        Parameters
        ----------
        image_url : `str`
            A direct URL to an image file.

        Returns
        -------
        `discord.Message`
            The Discord message belonging to the uploaded image.
        """

        # Get rehosting channel
        channel = self.bot.get_channel(config.IMAGE_CHANNEL_ID)

        # Check if url has an image extension
        file_name, ext = await self.get_filename_extension_from_url(image_url)
        if ext.lower() not in self.IMAGE_EXTENSIONS:
            raise FileTypeError("Attempted to upload a non-image file")

        # Get file-like bytes stream (io.BytesIO)
        file_bytes = await self.download_from_url(ctx, image_url)

        # Upload image
        f = discord.File(file_bytes, f"{file_name}.{ext}")
        msg = await channel.send(file=f)

        # Return message referencing image
        return msg

    async def upload_bytes_obj_to_discord(
        self, data: io.BytesIO, filename: str
    ) -> discord.Message:
        """Uploads a file-like io.BytesIO stream as a
        Discord file attachment

        Parameters
        ----------
        data : `io.BytesIO`
            File-like byte stream

        filename : `str`
            Filename + filetype. (FILETYPE IS REQUIRED!)

        Returns
        -------
        discord.Message
            Discord Message referencing uploaded file.
            File URL can be accessed via `msg.attachments[0].url`
        """

        channel = self.bot.get_channel(config.IMAGE_CHANNEL_ID)

        f = discord.File(data, filename)
        msg = await channel.send(file=f)

        return msg  # Could do return await.channel.send(), but I think this is more self documenting

    async def _get_cog_commands(
        self, ctx: commands.Context, advanced: bool = False
    ) -> str:
        """Sends an embed listing all commands belonging the cog.

        The method compiles a list of commands defined by the invoking cog,
        after which the list elements are string-formatted and added to
        an embed sent to the Discord channel `ctx.message.author.channel`.

        NOTE
        ----
        This method should only be invoked through a bot command.
        Argument `ctx` is required to have the `message.author.channel`
        attribute.

        Parameters
        ----------
        ctx : `commands.Context`
            Discord Context object
        advanced : `bool`, optional
            Defines whether the command listing should display calling
            signatures or not. (the default is False, which ommits signatures)
        """
        # Get commands for current cog
        # NOTE: Replace with walk_commands() to get subcommands?
        commands_ = await self.get_invokable_commands(ctx)
        commands_ = sorted(commands_, key=lambda cmd: cmd.name)

        # Get commands as string of command names + descriptions, separated by newlines
        out = []
        for command in commands_:

            # Skip commands that fail for current context or are hidden
            if not await command.can_run(ctx) or command.hidden or not command.enabled:
                continue

            group = False

            if isinstance(command, commands.Group):
                cmds = list(command.commands)
                cmds.sort(key=lambda k: k.name)
                cmds.insert(0, command)
                group = True
            else:
                cmds = [command]

            for cmd in cmds:
                # Show bot command prefix if command is not a subcommand
                subcommand = group and type(cmd) == commands.Command
                prefix = f"{self.bot.command_prefix}" if not subcommand else ""

                # Add indent to subcommands
                indent = (
                    f"-{self.EMBED_FILL_CHAR*2}"
                    if type(cmd) == commands.Command and subcommand
                    else ""
                )
                # Add right side padding if no indent
                padding = "\xa0" * 2 if not indent else ""

                # Show command signature on advanced output
                if advanced:
                    cmd_name = f"{cmd.name} {cmd.signature}".ljust(35, "\xa0")
                else:
                    cmd_name = cmd.name.ljust(20, "\xa0")

                # Add docstring prefix from check
                doc = cmd.short_doc
                for check in cmd.checks:
                    if hasattr(check, "doc_prefix"):
                        doc = f"{check.doc_prefix} {cmd.short_doc}"
                        break

                out.append(f"`{indent}{prefix}{cmd_name}{padding}:` {doc}")

        out_str = "\n".join(out)

        if advanced and out_str:
            # Add command signature legend string if advanced output is enabled
            out_str = self.SIGNATURE_HELP + out_str

        return out_str

    async def send_cog_commands(
        self, ctx: commands.Context, advanced: bool = False
    ) -> None:
        out = await self._get_cog_commands(ctx, advanced)
        if not out:
            raise CommandError("Cog has no commands!")
        await self.send_embed_message(
            ctx, f"{self.EMOJI} {self.cog_name} commands", out
        )

    async def send_text_message(
        self,
        text: str,
        ctx: Optional[commands.Context] = None,
        *,
        channel_id: Optional[int] = None,
    ) -> None:
        """
        Sends an arbitrarily long string as one or more messages to a channel.
        String is split into multiple messages if length of string exceeds
        Discord text message character limit.

        Parameters
        ----------
        ctx : `commands.Context`
            Discord Context
        text : `str`
            String to post to channel
        channel_id : `Optional[int]`, optional
            Optional channel ID if target channel is not part of the context.
        """
        # Obtain channel
        if ctx:
            channel = ctx
        elif channel_id:
            channel = self.bot.get_channel(channel_id)
        else:
            raise discord.DiscordException('"ctx" or "channel_id" must be specified')

        # Split string into chunks
        chunks = await self._split_string_to_chunks(text)

        # Send chunked messages
        for chunk in chunks:
            await channel.send(chunk)

    async def _split_string_to_chunks(self, text: str, limit: int = None) -> List[str]:
        """Splits a string into (default: 1800) char long chunks."""
        if not limit or limit > self.CHAR_LIMIT:
            limit = self.CHAR_LIMIT
        return [text[i : i + limit] for i in range(0, len(text), limit)]

    async def _split_string_by_lines(
        self, text: str, limit: int = None, strict: bool = False
    ) -> List[str]:
        """Splits a string into `limit`-sized chunks. DEFAULT: 1024

        The string is split into n<=limit sized chunks based on
        occurences of newline chars, whereas `BaseCog._split_string_to_chunks()`
        splits string into n<=limit chunks, with no regard for splitting
        words or sentences based on newline chars.
        """
        if not limit or limit > self.EMBED_CHAR_LIMIT:
            limit = self.EMBED_CHAR_LIMIT

        if len(text) < limit:  # no need to split
            return [text]

        chunk = ""  # Lines in a chunk
        chunk_len = 0  # Size of current chunk
        chunks = []

        for line in text.splitlines(keepends=True):
            line_len = len(line)

            # Handle lines whose length exceeds limit
            if line_len > limit:
                if strict:
                    raise discord.DiscordException(
                        "Unable to split string. Line length exceeds limit!"
                    )
                else:  # Fall back on _split_string_to_chunks()
                    return await self._split_string_to_chunks(text, limit)

            if chunk_len + line_len > limit:
                chunks.append(chunk)
                chunk = ""
                chunk_len = 0

            chunk += line
            chunk_len += line_len

        else:
            if chunk:
                chunks.append(chunk)

        return chunks

    async def send_embed_message(
        self,
        ctx: commands.Context,
        title: str,
        description: str,
        limit: int = None,
        message_text: str = None,
        footer: bool = True,
        keep_title: bool = False,
        channel: commands.TextChannelConverter = None,
        return_embeds: bool = False,
        **kwargs,
    ) -> Optional[List[discord.Embed]]:
        """Splits a string into <1024 char chunks and creates an
        embed object from each chunk, which are then sent to
        ctx.channel.

        Parameters
        ----------
        ctx : commands.Context
            Discord context
        title : str
            Embed title
        description : str
            Embed text
        limit : int, optional
            Embed text limit. Cannot exceed 1024.
        message_text : str, optional
            Message text displayed above embeds.
        footer : bool, optional
            Display footer on last embed
        keep_title : bool, optional
            Display title on every embed, by default False
        channel : commands.TextChannelConverter, optional
            Channel to post message to, by default ctx.message.author.channel
        return_embeds : bool, optional
            Return embeds instead of sending them to the channel, by default False

        Returns
        -------
        Optional[List[discord.Embed]]
            List of embed objects returned if `return_embeds==True`
        """
        # Split text by line
        if not limit or limit > self.EMBED_CHAR_LIMIT:
            limit = self.EMBED_CHAR_LIMIT

        text_fields = await self._split_string_by_lines(description, limit)

        if len(text_fields) > 1:
            t = title if keep_title else Embed.Empty
            embeds = [
                # Include header but no footer on first message
                await self.get_embed(
                    ctx, title=title, description=field, footer=False, **kwargs
                )
                if text_fields[0] == field
                else
                # Include footer but no header on last message
                await self.get_embed(
                    ctx, title=t, description=field, footer=footer, **kwargs
                )
                if text_fields[-1] == field
                else
                # No footer or header on middle message(s)
                await self.get_embed(
                    ctx, title=t, description=field, footer=False, **kwargs
                )
                for field in text_fields
            ]
        else:
            # Create normal embed with title and footer if text is not chunked
            embeds = [
                await self.get_embed(
                    ctx,
                    title=title,
                    description=text_fields[0],
                    footer=footer,
                    **kwargs,
                )
            ]

        # Return embed objects if enabled
        if return_embeds:
            return embeds

        # Send each embed object to ctx.channel
        if channel:
            ctx = channel

        for embed in embeds:
            # Add message text to first message
            if embed == embeds[0]:
                await ctx.send(content=message_text, embed=embed)
            else:
                await ctx.send(embed=embed)

    async def read_send_file(
        self, ctx: commands.Context, path: Union[str, Path], *, encoding: str = "utf-8"
    ) -> None:
        """Reads local text file and sends contents to `ctx.channel`"""
        async with AIOFile(path, "r", encoding=encoding) as f:
            await self.send_text_message(await f.read(), ctx)

    def generate_hex_color_code(
        self, phrase: str, *, as_int: bool = True
    ) -> Union[str, int]:
        """Generates a 24 bit hex color code from a user-defined phrase."""
        p = str(phrase).encode()
        h = hashlib.blake2b(p, digest_size=3, key=b"vjemmie")
        if as_int:
            return int(h.hexdigest(), 16)
        return h.hexdigest()

    async def get_filename_extension_from_url(self, url: str) -> tuple:
        """Get filename and extension from a URL."""
        fname, extension = os.path.splitext(os.path.basename(urlsplit(url).path))

        if not extension:
            raise discord.DiscordException("URL has no file extension")

        return fname, extension

    async def is_img_url(self, url: Union[str, discord.Asset]) -> bool:
        """Checks if a string is an HTTP/HTTPS URL to an image file"""
        # Get url string if url argument is a discord.Asset object
        if isinstance(url, discord.Asset):
            url = str(url)

        p = urlparse(url)
        return (
            p.scheme in ["http", "https"]
            and any(p.path.lower().endswith(ext) for ext in self.IMAGE_EXTENSIONS)
            and p.hostname is not None
            and not url.endswith(p.hostname)
        )

    async def log_file_download(
        self,
        ctx: commands.Context,
        *,
        url: str = None,
        filename: str = None,
        msg: str = None,
    ) -> None:
        """Logs file download to log channel.

        Parameters
        ----------
        ctx : `commands.Context`
            Discord context
        url : `str`, optional
            URL file was downloaded from
        filename : `str`, optional
            Filename
        msg : `str`, optional
            String to override default log message body with
        """
        author = ctx.message.author
        guild = ctx.message.author.guild
        if not msg:
            msg = f"**`{author}`** from **`{guild}`** downloaded **`{filename}`** from {url}"
        await self.send_text_message(msg, channel_id=config.DOWNLOAD_CHANNEL_ID)

    async def check_downloads_permissions(
        self, *, message: str = None, add_msg: str = None
    ) -> None:
        """Checks download permissions defined in `config.py`.

        Parameters
        ----------
        message : `str`, optional
            Override base exception message
        add_msg : `str`, optional
            String to add to existing exception message

        Raises
        ------
        `PermissionError`
            Raised if downloads are disabled in config
        """

        msg = message or "Bot owner has disabled downloads!"
        if add_msg:
            msg += f" {add_msg}"
        if not config.DOWNLOADS_ALLOWED:
            raise BotPermissionError(msg)

    async def get_cogs(self, *, all_cogs: bool = False) -> list:
        """Returns list of cogs, sorted by name. Optionally includes
        cogs hidden by `BaseCog.DISABLE_HELP`.

        NOTE
        ----
        I might remove the `all_cogs` parameter and fully respect that
        disabled means disabled.
        """
        return sorted(
            [
                cog
                for cog in self.bot.cogs.values()
                if cog.DISABLE_HELP
                in [False, all_cogs]  # [False, True] or [False, False]
                and cog.cog_name != "BotSetup"
            ],
            key=lambda c: c.cog_name,
        )

    async def get_embed_from_img_upload(
        self,
        ctx: commands.Context,
        to_upload: Union[io.BytesIO, str],
        filename: Optional[str] = None,
    ) -> discord.Embed:
        """Uploads an image to Discord from a URL or a file-like object
        and returns a `discord.Embed` object.

        Parameters
        ----------
        ctx : `commands.Context`
            Discord context
        to_upload : `Union[io.BytesIO, str]`
            Image to upload
        filename : `Optional[str]`, optional
            Filename + extension of image.
            Mandatory if `to_upload` is a file-like object.

        Raises
        ------
        `ValueError`
            Raised if URL cannot be recognized as an image URL.
        `TypeError`
            Raised if `to_upload` is a file-like object and
            filename is None.
        `ValueError`
            Raised if `filename` does not contain a file extension.
        `TypeError`
            Raised if `to_upload` is neither type `str` nor `io.BytesIO`.

        Returns
        -------
        `discord.Embed`
            Discord embed object.
        """
        if isinstance(to_upload, str):
            # String must be an image URL
            if not self.is_img_url(to_upload):
                raise ValueError("String must be URL to an image file!")

            # Upload image to bot's image rehosting channel
            msg = await self.rehost_image_to_discord(ctx, to_upload)
            url = msg.attachments[0].url

        elif isinstance(to_upload, io.BytesIO):
            # Check if filename is passed in
            if not filename:
                raise TypeError("A filename is required for bytes object uploads!")

            # Check if filename contains name of file and extension
            fname, ext = os.path.splitext(filename)
            if not ext:
                raise ValueError(
                    "Filename must contain name of file and extension, e.g. 'image.jpeg'"
                )

            # Upload image and get URL from resulting bot message
            msg = await self.upload_bytes_obj_to_discord(to_upload, filename)
            url = msg.attachments[0].url

        else:
            raise TypeError('Argument "to_upload" must be type <io.BytesIO> or <str>')

        # Create discord Embed object using obtained URL of image
        return await self.get_embed(ctx, image_url=url)

    def reset_command_cooldown(self, ctx: commands.Context) -> None:
        cmd = ctx.command
        cmd.reset_cooldown(ctx)

    async def get_command_invocation_ctx(self) -> commands.Context:
        channel = self.bot.get_channel(config.COMMAND_INVOCATION_CHANNEL)
        ctx = await self.bot.get_context(
            await channel.fetch_message(channel.last_message_id)
        )
        return ctx

    async def get_invokable_commands(self, ctx) -> List[commands.Command]:
        return [
            command
            for command in self.bot.commands
            if command.cog == self
            and not command.hidden
            and command.enabled
            and await command.can_run(ctx)
        ]

    async def filter_user_mapping(
        self, mapping: Mapping[Union[int, discord.User], Any]
    ) -> List[Tuple[discord.User, Any]]:
        # Convert to list to grab by index
        if isinstance(mapping, Mapping):
            mapping = list(mapping.items())
        else:
            mapping = list(mapping)  # not pretty

        first_key = mapping[0][0]  # assume keys are homogenous

        # Silently support str keys
        # (if loading a json file, where int keys are not supported)
        if isinstance(first_key, str):
            try:
                int(first_key)
            except ValueError:
                raise TypeError("Mapping keys must be Discord user IDs, not strings.")

        if not any(isinstance(first_key, t) for t in [int, str, discord.User]):
            raise TypeError("Mapping keys must be either type 'int' or 'discord.User'")

        # Get discord.User objects if keys are int or str
        if any(isinstance(first_key, t) for t in [int, str]):
            mapping = [
                # Try to retrieve users from bot's cache, otherwise fetch from API
                (await get_user(self.bot, int(k)), v)
                for k, v in mapping
            ]
        # Filter users who cannot be found
        l = list(filter(lambda m: None.__ne__(m[0]), mapping))

        return l

    async def _format_user_mapping(
        self,
        mapping: List[Tuple[discord.User, Any]],
    ) -> str:
        longest_name = max([len(k.name) for k, _ in mapping])
        fchar = self.EMBED_FILL_CHAR  # to make expression more readable
        return "\n".join(
            [f"`{k.name.ljust(longest_name, fchar)}:`{fchar*3}{v}" for k, v in mapping]
        )

    async def send_key_value_message(
        self,
        ctx: commands.Context,
        mapping: Mapping[Union[int, discord.User], Any],
        title: str,
        *,
        sort: bool = True,
        thumbnail: bool = True,
        **kwargs,
    ) -> None:
        # Get message body
        m = await self.filter_user_mapping(mapping)
        if not m:
            raise ValueError("No valid users found in mapping.")
        if sort:
            m = sorted(m, key=lambda i: i[1], reverse=True)
        desc = await self._format_user_mapping(m)

        if thumbnail:
            thumbnail_url = m[0][0].avatar_url
        else:
            thumbnail_url = None

        await self.send_embed_message(
            ctx, title=title, description=desc, thumbnail_url=thumbnail_url, **kwargs
        )
