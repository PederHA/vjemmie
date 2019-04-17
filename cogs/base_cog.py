import hashlib
import io
import os.path
import traceback
from collections import namedtuple
from datetime import datetime, timedelta
from io import BytesIO
from typing import Iterable, Iterator, List, Optional, Union
from urllib.parse import urlparse, urlsplit

import aiohttp
import discord
import requests
from discord.ext import commands

from config import (DOWNLOADS_ALLOWED, AUTHOR_MENTION, #DISABLE_HELP,
                    DOWNLOAD_CHANNEL_ID, IMAGE_CHANNEL_ID, LOG_CHANNEL_ID,
                    MAX_DL_SIZE, GUILD_HISTORY_CHANNEL)

md_formats = ['asciidoc', 'autohotkey', 'bash',
            'coffeescript', 'cpp', 'cs', 'css',
            'diff', 'fix', 'glsl', 'ini', 'json',
            'md', 'ml', 'prolog', 'py', 'tex',
            'xl', 'xml']

EmbedField = namedtuple("EmbedField", "name value")

class InvalidFiletype(Exception):
    """Invalid filetype in a given context"""

class FileSizeError(Exception):
    """File Size too small or too large"""

class BaseCog(commands.Cog):
    """Base Cog from which all other cogs are subclassed."""

    # Cogs to ignore when creating !help commands
    DISABLE_HELP = False

    # Valid image extensions to post to a Discord channel
    IMAGE_EXTENSIONS = [".jpeg", ".jpg", ".png", ".gif", ".webp"]

    # Channel and User IDs
    IMAGE_CHANNEL_ID = IMAGE_CHANNEL_ID
    LOG_CHANNEL_ID = LOG_CHANNEL_ID
    DOWNLOAD_CHANNEL_ID = DOWNLOAD_CHANNEL_ID
    GUILD_HISTORY_CHANNEL = GUILD_HISTORY_CHANNEL
    AUTHOR_MENTION = AUTHOR_MENTION

    # Download options
    MAX_DL_SIZE = MAX_DL_SIZE
    DOWNLOADS_ALLOWED = DOWNLOADS_ALLOWED

    # Embed Options
    EmbedField = namedtuple("EmbedField", "name value")
    CHAR_LIMIT = 1800
    EMBED_CHAR_LIMIT = 1000
    EMBED_FILL_CHAR = "\xa0"

    # Style info for help categories
    EMOJI = ":question:"

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.add_help_command()

    @property
    def cog_name(self) -> str:
        cog_name = self.__class__.__name__
        return cog_name if not cog_name.endswith("Cog") else cog_name[:-3]

    @property
    def MAX_DL_SIZE_FMT(self) -> str:
        size_mb = self.MAX_DL_SIZE / 1_000_000
        return f"{size_mb} MB"

    def add_help_command(self) -> None:
        #if self.cog_name not in self.DISABLE_HELP:
        if not self.DISABLE_HELP:
            cmd_coro = self._get_cog_commands
            cmd = commands.command(name=self.cog_name)(cmd_coro)
            self.bot.add_command(cmd)

    async def format_output(self, items: Iterable, *, formatting: str="", item_type: str=None, enum: bool=False) -> str:
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
        item_type : `str`, optional
            Description of items in iterable. Default: None
        enum : `bool`, optional
            Adds index number next to each item listing. Default: False
        
        Returns
        -------
        output : `str`
            Markdown formatted code block of items in iterable, 1 item per line.

        Example
        -------
        >>>format_output(["foo", "bar", "baz"], "generic items")
        '```
        Available generic items:

        1. foo
        2. bar
        3. baz
        ```'
        """
        if formatting not in md_formats:
            formatting = ""

        output = f"```{formatting}\n"
        if item_type is not None:
            output += f"Available {item_type}:\n\n"
        idx = ""
        for i, item in enumerate(items, 1):
            if enum:
                idx = f"{i}. "
            output += f"{idx}{item}\n"
        else:
            output += "```"
        return output

    async def make_codeblock(self, content:str, md_format: str=None) -> str:
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
                raise discord.DiscordException(f"Could not interpret {color}")
            else:
                return color_classmethod()
        
        # Parse int arg
        elif isinstance(color, int):
            return discord.Color(color)
        
        else:
            raise discord.DiscordException("Argument must be type(str) or type(int)")

    async def get_embed(self,
                        ctx: commands.Context,
                        *,
                        title: str=None,
                        footer: bool=True,
                        fields: Optional[list]=None,
                        image_url: str=None,
                        color: Union[str, int]=None,
                        timestamp: bool=True,
                        inline: bool=True) -> discord.Embed:
        """Constructs a discord.Embed object.
        
        Parameters
        ----------
        ctx : `commands.Context`
            Discord Context
        title : `str`, optional
            Title of embed. A single line of bolded text at the top of the embed.
        footer : `bool`, optional
            Display footer on embed in the format:
            <user avatar> <"requested by `user`"> <timestamp>
        fields : `list`, optional
            List of EmbedField objects. Each EmbedField is added as a
            new field to the embed via `embed.add_field`
        image_url : `str`, optional
            Image URL. TODO: Add more info
        color : `Optional[str, int]`, optional
            Color of embed. Can be specified as str or int.
            See `BaseCog.get_discord_color` for info.
        timestamp : `bool`, optional
            Display timestamp on footer. Has no effect if 
            param `footer=False`
        inline : `bool`, optional
            Display embed fields inline.
        
        Returns
        -------
        discord.Embed
            A Discord embed object that can be sent to a text channel
        """

        opts = {"timestamp":datetime.now()} if timestamp else {}
        embed = discord.Embed(title=title, **opts)
        
        if footer:
            embed.set_footer(text=f"Requested by {ctx.message.author.name}", icon_url=ctx.message.author.avatar_url)
        
        if fields:
            for field in fields:
                embed.add_field(name=field.name, value=field.value, inline=inline)
        
        if image_url:
            embed.set_image(url=image_url)
        
        if color:
            _color = await self.get_discord_color(color)
            embed.color = _color
        
        return embed

    async def get_users_in_voice(self, ctx: commands.Context, nick: bool=False) -> Iterator[str]:
        """
        Generator of discord users in voice channel of ctx.message.author.
        """
        if not hasattr(ctx.message.author.voice, "channel"):
            raise AttributeError("Message author is not connected to a voice channel.")

        for member in ctx.message.author.voice.channel.members:
            if member.nick and nick:
                yield member.nick
            else:
                yield member.name

    async def send_log(self, msg: str, *, channel_id: int=None) -> None:
        """Sends log message to log channel
        
        Parameters
        ----------
        msg : `str`
            String to send as message to log channel
        """
        if not channel_id:
            channel_id = self.LOG_CHANNEL_ID

        try:     
            await self.send_text_message(msg, channel_id=channel_id)
        except discord.Forbidden:
            print(f"Insufficient permissions for channel {channel_id}.")
        except discord.HTTPException:
            print(f"Failed to send message to channel {channel_id}.")

    async def log_error(self, ctx: commands.Context, error_msg: str) -> None:
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

        # Send traceback
        await self.send_text_message(error_msg, channel_id=self.LOG_CHANNEL_ID)
        
        # Send message that caused error
        cause_of_error = f"Message that caused error: {ctx.author.name}: {ctx.message.content}" if ctx else ""
        await self.send_text_message(cause_of_error, channel_id=self.LOG_CHANNEL_ID)

    async def cog_command_error(self, ctx: commands.Context, error: Exception, *bugged_params) -> None:
        """Handles exceptions raised by commands defined in the cog.

        This method is added to every bot command by 
        `BaseCog._add_error_handlers()` with the exception
        of those commands that define their own error handlers.

        Parameters
        ----------
        ctx : commands.Context
            Discord Context object
        error : Exception
            Exception that was raised
        """
        # NOTE: The paragraph under might be incorrect after the new `cog_command_error()` method was added

        # Sometimes two instances of the class instance is passed in, totaling 4 args instead of 3
        # My hypothesis might be wrong here, and the extra arg actually has a purpose
        # I have not investigated it properly
        if bugged_params:
            ctx = error
            error = bugged_params[0]

        # Check if error stems from lack of privileges
        if isinstance(error, commands.CheckFailure):
            return await ctx.send("Insufficient privileges to perform command!")

        if hasattr(error, "original"):
            return await self.send_error_msg(ctx, error.original.args[0])

        # Get error message
        if hasattr(error, "original"):
            # Result of raised exception
            # `raise discord.DiscordException("error")`
            error_msg = error.original.args[0]
            #return await self._unknown_error(ctx, error_msg)
        else:
            # Result of "real" exception
            # `n = 1 / 0`
            error_msg = error.args[0]

        await self._unknown_error(ctx, error_msg)

    # UNFINISHED
    async def parse_error(self, error: BaseException) -> None:
        if isinstance(error.original, PermissionError):
            return error.original.args[0]

    async def _unknown_error(self, ctx: commands.Context, error_msg: str):
        """Method called when raised exception is not recognized
        by `BaseCog.cog_command_error()`
        
        Parameters
        ----------
        ctx : `commands.Context`
            Discord Context object
        error_msg : `str`
            Error message
        """
        # List of error messages to ignore
        ignore = []
        if not any(x in error_msg for x in ignore):
            out_msg = f"**Error:** {error_msg}"
        else:
            out_msg = "An error occured."
        await ctx.send(out_msg) # Display error to user

        # Get formatted traceback
        traceback_msg = traceback.format_exc()
        await self.log_error(ctx, traceback_msg) # Send entire exception traceback to log channel

    async def get_aiohttp_session(self, ctx: commands.Context) -> aiohttp.ClientSession:
        """Retrieves per-guild aiohttp.ClientSession session object. 
        Session is created for the guild if it has no active sessions.
        
        Parameters
        ----------
        ctx : `commands.Context`
            Discord context
        
        Raises
        ------
        PermissionError
            Raised if downloads are disabled in `config.py`
        
        Returns
        -------
        aiohttp.ClientSession
            aiohttp session for guild
        """

        # Check if downloads are enabled in config. 
        if not self.DOWNLOADS_ALLOWED:
            raise PermissionError("Downloads are not allowed for this bot!")
        
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
        # Get session
        session = await self.get_aiohttp_session(ctx)
        
        # Check if host responds
        try:
            resp = await session.get(url)
        except aiohttp.ClientConnectionError:
            raise discord.DiscordException("No response from destination host")
        
        # Check content size
        if resp.content_length > self.MAX_DL_SIZE:
            raise FileSizeError(f"File exceeds maximum limit of {self.MAX_DL_SIZE_FMT}")
        
        # Download content
        data = await resp.read()
        
        return io.BytesIO(data)
    
    async def rehost_image_to_discord(self, ctx: commands.Context, image_url: str=None) -> discord.Message:
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
        channel = self.bot.get_channel(self.IMAGE_CHANNEL_ID)

        # Check if url has an image extension
        file_name, ext = await self.get_filename_extension_from_url(image_url)
        if ext.lower() not in self.IMAGE_EXTENSIONS:
            raise InvalidFiletype("Attempted to upload a non-image file")

        # Get file-like bytes stream (io.BytesIO)
        file_bytes = await self.download_from_url(ctx, image_url)

        # Upload image
        f = discord.File(file_bytes, f"{file_name}.{ext}")
        msg = await channel.send(file=f)

        # Return message referencing image
        return msg

    async def upload_bytes_obj_to_discord(self, data: io.BytesIO, filename: str) -> discord.Message:
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

        channel = self.bot.get_channel(self.IMAGE_CHANNEL_ID)

        f = discord.File(data, filename)
        msg = await channel.send(file=f)

        return msg # Could do return await.channel.send(), but I think this is more self documenting

    async def _get_cog_commands(self, ctx: commands.Context, output_style: str="simple", *, rtn: bool=False) -> None:
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
        simple : `bool`, optional
            Defines whether the command listing should display calling
            signatures or not. (the default is True, which ommits signatures)
        """
        # Toggle simple/advanced output
        simple = True if output_style == "simple" else False
        
        # Get commands for current cog
        _commands = sorted(self.get_commands(),key=lambda cmd: cmd.name)
        
        # Get commands as string of command names + descriptions, separated by newlines
        _out_str = ""
        for command in _commands:
            # Hide commands that fail for current context
            check_failed = False
            for check in command.checks:
                if not check(ctx):
                    check_failed = True
                    break
            if check_failed:
                continue
            
            if simple:
                cmd_name = command.name.ljust(20,"\xa0")
            else:
                cmd_name = command.signature.ljust(35,"\xa0")
            _out_str += f"`!{cmd_name}:`\xa0\xa0\xa0\xa0{command.short_doc}\n"
        
        if not _out_str:
            return await self.send_error_msg(ctx, "Cog has no commands!")
        
        if rtn:
            return _out_str
        
        await self.send_embed_message(ctx, f"{self.EMOJI} {self.cog_name} commands", _out_str)

    async def send_text_message(self, 
                                text: str,     
                                ctx: Optional[commands.Context]=None,
                                *,
                                channel_id: Optional[int]=None) -> None:
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
            channel = ctx.message.channel
        elif channel_id:
            channel = self.bot.get_channel(channel_id)
        else:
            raise Exception('"ctx" or "channel_id" must be specified')

        # Split string into chunks
        chunks = await self._split_string_to_chunks(text)

        # Send chunked messages
        for chunk in chunks:
            await channel.send(chunk)

    async def _split_string_to_chunks(self, text: str, limit: int=None) -> List[str]:
        """Splits a string into (default: 1800) char long chunks."""
        if not limit or limit>self.CHAR_LIMIT:
            limit = self.CHAR_LIMIT
        return [text[i:i+limit] for i in range(0, len(text), limit)]

    async def _split_string_by_lines(self, text: str, limit: int=None) -> List[str]:
        """Splits a string into `limit`-sized chunks. DEFAULT: 1024
        
        String is split into lines as denoted by newline char, then lines are
        joined into n<=limit sized chunks, whereas `_split_string_to_chunks()` 
        splits string into n<=limit chunks, ignoring any newline chars.
        """
        if not limit or limit > 1024: # NOTE: This shouldn't be hardcoded
            limit = self.CHAR_LIMIT
        
        temp = ""
        for line in text.splitlines():
            l = f"{line}\n"
            if len(temp + l) > limit:
                yield temp
                temp = ""
            temp += l
        else:
            if len(temp) > limit:
                raise ValueError(
                    "String does not have enough newline characters to split by!"
                    )
            if temp:
                yield temp

    async def send_embed_message(self,
                                         ctx: commands.Context,
                                         header: str,
                                         text: str,
                                         limit: int=None,
                                         *,
                                         color: Union[str, int]=None,
                                         return_embeds: bool=False,
                                         footer: bool=True,
                                         timestamp: bool=True) -> Optional[List[discord.Embed]]:
        """Splits a string into <1024 char chunks and creates an
        embed object from each chunk, which are then sent to 
        ctx.channel.
        
        Parameters
        ----------
        ctx : `commands.Context`
            Discord Context
        header : `str`
            Title of embed
        text : `str`
            Text included in embed field(s)
        limit : `int`, optional
            Character limit. Cannot exceed 1024.
        return_embeds : `bool`, optional
            If True, returns chunked message as list of 
            embed objects instead of sending them to ctx.channel.
        """
        # Split text by line
        if not limit or limit > self.EMBED_CHAR_LIMIT:
            limit = self.EMBED_CHAR_LIMIT
        
        text_fields = [tf async for tf in self._split_string_by_lines(text, limit)]

        if len(text_fields) > 1:
            embeds = [
                # Include header but no footer on first message
                await self.get_embed(ctx, fields=[EmbedField(header, field)], footer=False, timestamp=False, color=color)
                if text_fields[0] == field else
                # Include footer but no header on last message
                await self.get_embed(ctx, fields=[EmbedField("_", field)], footer=footer, timestamp=timestamp, color=color)
                if text_fields[-1] == field else
                # No footer or header on middle message(s)
                await self.get_embed(ctx, fields=[EmbedField("_", field)], footer=False, timestamp=False, color=color)
                for field in text_fields]
        else:
            # Create normal embed with title and footer if text is not chunked
            embeds = [
                await self.get_embed(
                    ctx,
                    fields=[EmbedField(header, text_fields[0])],
                    footer=footer,
                    timestamp=timestamp,
                    color=color)
            ]

        # Return embed objects if enabled
        if return_embeds:
            return embeds

        # Send each embed object to ctx.channel
        for embed in embeds:
            await ctx.send(embed=embed)

    async def read_send_file(self, ctx: commands.Context, path: str, *, encoding: str="utf-8") -> None:
        """Reads local text file and sends contents to `ctx.channel`"""
        with open(path, "r", encoding=encoding) as f:
            await self.send_text_message(f.read(), ctx)

    def generate_hex_color_code(self, phrase: str, *, as_int: bool=True) -> Union[str, int]:
        """Generates a 24 bit hex color code."""
        phrase = str(phrase).encode()
        h = hashlib.blake2b(phrase, digest_size=3, key=b"vjemmie")
        if as_int:
            return int(h.hexdigest(), 16)
        return h.hexdigest()

    async def get_filename_extension_from_url(self, url: str) -> tuple:
        """Get filename and extension from a URL."""
        fname, extension = os.path.splitext(
            os.path.basename(urlsplit(url).path))

        if not extension:
            raise AttributeError("URL has no file extension")

        return fname, extension

    async def is_img_url(self, url: str) -> bool:
        """Checks if a string is an HTTP/HTTPS URL to an image file"""
        return (
                urlparse(url).scheme in ["http", "https"] and
                any(("."+url.rsplit(".", 1)[1].lower()).startswith(ext) 
                for ext in self.IMAGE_EXTENSIONS)
                )

    async def send_error_msg(self, ctx: commands.Context, msg: str) -> None:
        """Sends text message to `ctx.channel` prepended with error-text."""
        await self.send_text_message(f"**ERROR:** {msg}", ctx)

    async def log_file_download(self,
                                ctx: commands.Context,
                                *,
                                url: str=None,
                                filename: str=None,
                                msg: str=None) -> None:
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
        await self.send_text_message(msg, channel_id=self.DOWNLOAD_CHANNEL_ID)

    async def check_downloads_permissions(self, *, message: str=None, add_msg: str=None) -> None:
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
        if not self.DOWNLOADS_ALLOWED:
            raise PermissionError(msg)
        
    async def get_cogs(self, *, all_cogs: bool=False) -> list:
        """Returns list of cogs, sorted by name. Optionally includes
        cogs hidden by `BaseCog.DISABLE_HELP`.
        
        NOTE
        ----
        I might remove the `all_cogs` parameter and fully respect that
        disabled means disabled.
        """
        filtering = True if all_cogs else False
        return sorted([
                        cog for cog in self.bot.cogs.values() 
                        if cog.DISABLE_HELP in [False, filtering]
                       ],
                    key=lambda c: c.cog_name)

    async def get_embed_from_img_upload(self,
                                        ctx: commands.Context,
                                        to_upload: Union[io.BytesIO, str], 
                                        filename: Optional[str]=None
                                        ) -> discord.Embed:
        # TODO: singledispatch?
        
        if isinstance(to_upload, str):
            if not self.is_img_url(to_upload):
                raise ValueError("String must be URL to an image file!")
            
            msg = await self.rehost_image_to_discord(ctx, to_upload)
            url = msg.attachments[0].url
            _fname, ext = self.get_filename_extension_from_url(url)
            filename = f"{_fname}.{ext}"
        
        elif isinstance(to_upload, io.BytesIO):
            if not filename: 
                raise TypeError("A filename is required for bytes object uploads!")
            msg = await self.upload_bytes_obj_to_discord(to_upload, filename)
            url = msg.attachments[0].url
        
        else:
            raise TypeError('Argument "to_upload" must be type <io.BytesIO> or <str>')
        
        embed = await self.get_embed(ctx, image_url=url)
        return embed