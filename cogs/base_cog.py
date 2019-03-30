import traceback
import hashlib
import os.path
from io import BytesIO
import io
from urllib.parse import urlsplit
from collections import namedtuple
from datetime import datetime, timedelta
from typing import Iterable, List, Optional, Union

import aiohttp
import discord
import requests
from discord.ext import commands
from ext.checks import is_pfm

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
    """
    Base Cog from which all other cogs are subclassed.
    """

    # Cogs to ignore when creating !help commands
    IGNORE_HELP = ["Admin", "Base", "Cod", "Weather", "YouTube", "War3"]

    # Valid image extensions to post to a Discord channel
    IMAGE_EXTENSIONS = [".jpeg", ".jpg", ".png", ".gif", ".webp"]
    MAX_DL_SIZE = 25_000_000 # 25 MB

    # Channel and User IDs
    IMAGE_CHANNEL_ID = 549649397420392567
    LOG_CHANNEL_ID = 340921036201525248
    AUTHOR_MENTION = "<@103890994440728576>"

    # Embed Options
    EmbedField = namedtuple("EmbedField", "name value")
    CHAR_LIMIT = 1800
    EMBED_CHAR_LIMIT = 1000
    EMBED_FILL_CHAR = "\xa0"

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
        command_name = self.cog_name
        if command_name != "base" and command_name not in self.IGNORE_HELP:
            cmd_coro = self._get_cog_commands
            cmd = commands.command(name=command_name)(cmd_coro)
            self.bot.add_command(cmd)

    async def format_output(self, items: Iterable, *, formatting: str="", item_type: str=None, enum: bool=False) -> str:
        """
        Creates a multi-line codeblock in markdown formatting
        listing items in iterable `items` on separate lines.

        Args:
            items (Iterable): Iterable of items to be represented
            item_type (str): (optional) Description of items in iterable. Default: None
            enum: (optional) Generates index next to each item listing. Default: False
        
        Returns:
            output (str): Markdown formatted code block listing items in iterable, 1 per line.

        Example:
            >>>format_output(["foo", "bar", "baz"], "generic items")
            ```Available generic items:

            1. foo
            2. bar
            3. baz
            ```
        
        TODO: Split messages longer than 1800 chars
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

    async def get_embed_field(self, name, value) -> EmbedField:
        return EmbedField(name, value)

    async def get_discord_color(self, color: Union[str, int]) -> discord.Color:
        """Returns a discord.Color object corresponding to a color specified
        by name via string or as an integer value
        
        Parameters
        ----------
        color : Union[str, int]
            Color specified as string literal:
                >>> get_discord_color("red")
            Or as hexadecimal integer literal:
               >>> get_discord_color(0x4a998a)
        
        Raises
        ------
        discord.DiscordException
            If discord.Color has no attribute with name `color`
        discord.DiscordException
            If type of argument `color` is neither `int` nor `str`
        
        Returns
        -------
        discord.Color
            A discord.Color object initialized with the desired color
        """
        if isinstance(color, str):
            try:
                color_func = getattr(discord.Color, color)
            except:
                raise discord.DiscordException(f"Could not interpret {color}")
            else:
                return color_func()
        elif isinstance(color, int):
            return discord.Color(color)
        else:
            raise discord.DiscordException("Could not obtain color")

    async def get_embed(self,
                        ctx: commands.Context,
                        *,
                        title: str=None,
                        footer: bool=True,
                        fields: Optional[list]=None,
                        image_url: str=None,
                        color: Union[str, int]=None,
                        timestamp: bool=True) -> discord.Embed:
        """Constructs a discord embed object.
        
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
                embed.add_field(name=field.name, value=field.value)
        if image_url:
            embed.set_image(url=image_url)
        if color:
            _color = await self.get_discord_color(color)
            embed.color = _color
        return embed

    async def get_users_in_voice(self, ctx: commands.Context, nick: bool=False) -> list:
        """
        Returns list of discord users in voice channel of ctx.message.author.
        """
        users = []
        if ctx.message.author.voice.channel.members is not None:
            for member in ctx.message.author.voice.channel.members:
                if member.nick != None and nick:
                    users.append(member.nick)
                else:
                    users.append(member.name)
        else:
            raise AttributeError("Message author is not connected to a voice channel.")
        return users

    async def send_log(self, msg: str, ctx: Optional[commands.Context]=None) -> None:
        """Sends log message to log channel.

        If param `ctx` is not None, `send_log` assumes an error has occured,
        and includes the bot command that triggered the error and the user
        that used it.
        
        Args:
            msg (str): Message to be logged
            ctx (commands.Context, optional): a `discord.ext.commands.Context` object of message
            that caused an error
        """
        try:
            cause_of_error = f"\n\nMessage that caused error: {ctx.author.name}: {ctx.message.content}" if ctx else ""
            await self.send_text_message(ctx, msg, channel_id=self.LOG_CHANNEL_ID)
            if cause_of_error:
                await self.send_text_message(ctx, cause_of_error, channel_id=self.LOG_CHANNEL_ID)
        except discord.Forbidden:
            print(f"Insufficient permissions for channel {self.LOG_CHANNEL_ID}.")
        except discord.HTTPException:
            print(f"Failed to send message to channel {self.LOG_CHANNEL_ID}.")

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

        # Get error message
        if hasattr(error, "original"):
            # Result of raised exception
            # `raise discord.DiscordException("error")`
            error_msg = error.original.args[0]
        else:
            # Result of "real" exception
            # `n = 1 / 0`
            error_msg = error.args[0]

        if "The check functions" in error_msg: # lack of user privileges
            await ctx.send("Insufficient rights to perform command!")
        else:
            await self._unknown_error(ctx, error_msg)

    async def _unknown_error(self, ctx: commands.Context, error_msg: str):
        """Method called when raised exception is not recognized
        by `BaseCog.cog_command_error()`
        
        Parameters
        ----------
        ctx : commands.Context
            Discord Context object
        error_msg : str
            Error message of exception FIXME: Word this better than a brain damaged chimpanzee
        
        """

        # List of error messages to ignore
        ignore = []
        if not any(x in error_msg for x in ignore):
            out_msg = f"**Error:** {error_msg}"
        else:
            out_msg = "An unknown error occured"
        await ctx.send(out_msg) # Display error to user

        # Get formatted traceback
        traceback_msg = traceback.format_exc()
        await self.send_log(traceback_msg, ctx) # Send entire exception traceback to log channel

    async def download_from_url(self, url: str) -> io.BytesIO: # TODO: FIX
        """Downloads the contents of URL `url` and returns an `io.BytesIO` object.
        
        Returns
        -------
        `bytes`
            The downloaded content of the URL
        """
        async with aiohttp.ClientSession() as session:
            r = await session.get(url)
            if r.content_length > self.MAX_DL_SIZE:
                raise FileSizeError(f"File exceeds maximum limit of {self.MAX_DL_SIZE_FMT}")
            img = await r.read()
            return io.BytesIO(img)

    async def rehost_image_to_discord(self, image_url: str=None) -> discord.Message:
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

        # Get file-like bytes object (io.BytesIO)
        file_bytes = await self.download_from_url(image_url)

        # Upload image
        f = discord.File(file_bytes, f"{file_name}.{ext}")
        msg = await channel.send(file=f)

        # Return message referencing image
        return msg

    async def upload_bytes_obj_to_discord(self, data: io.BytesIO, filename: str) -> discord.Message:
        """Uploads a bytesIO stream(?) as a Discord file attachment
        
        Parameters
        ----------
        data : `io.BytesIO`
            Bytes-encoded data
        
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

    async def _get_cog_commands(self, ctx: commands.Context, output_style: str="simple") -> None:
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
        simple = True if output_style == "simple" else False
        _commands = sorted(self.get_commands(),key=lambda cmd: cmd.name)
        _out_str = ""
        for command in _commands:
            if simple:
                cmd_name = command.name.ljust(20,"\xa0")
            else:
                cmd_name = command.signature.ljust(35,"\xa0")
            _out_str += f"`!{cmd_name}:`\xa0\xa0\xa0\xa0{command.short_doc}\n"
        if not _out_str:
            return
        await self.send_embed_message(ctx, f"{self.cog_name} commands", _out_str)

    async def send_text_message(self, ctx: commands.Context, text: str, *, channel_id: Optional[int]=None) -> None:
        """
        Posts an arbitrarily long string as a message to a channel.

        Message is split into multiple parts if string exceeds 1800 characters.
        
        Parameters
        ----------
        ctx : commands.Context
            Discord Context
        text : str
            String to post to channel
        channel_id : Optional[int], optional
            Optional channel ID if target channel is not part of the context.
        """
        # Obtain channel
        if channel_id:
            channel = self.bot.get_channel(channel_id)
        else:
            channel = ctx.message.channel

        # Split string into chunks
        chunks = await self._split_string_to_chunks(text)

        # Send chunked messages
        for chunk in chunks:
            await channel.send(chunk)

    async def _split_string_to_chunks(self, text: str) -> List[str]:
        """Splits a string into (default: 1800) char long chunks."""
        LIMIT = self.CHAR_LIMIT # Makes list comprehension easier to read
        return [text[i:i+LIMIT] for i in range(0, len(text), LIMIT)]

    async def _split_string_by_lines(self, text: str, limit: int=None) -> List[str]:
        if not limit or limit > 1024:
            limit = self.CHAR_LIMIT
        _out = []
        temp = ""
        for line in text.splitlines():
            l = f"{line}\n"
            if len(temp + l) > limit:
                _out.append(temp)
                temp = ""
            temp += l
        else:
            _out.append(temp)
        return _out

    async def send_embed_message(self,
                                         ctx: commands.Context,
                                         header: str,
                                         text: str,
                                         limit: int=None,
                                         *,
                                         color: Union[str, int]=None,
                                         return_embeds: bool=False,
                                         footer: bool=True,
                                         timestamp: bool=True) -> Optional[list]:
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
        text_fields = await self._split_string_by_lines(text, limit)

        if len(text_fields) > 1:
            embeds = [
                # Include header but no footer on first message
                await self.get_embed(ctx, fields=[self.EmbedField(header, field)], footer=False, timestamp=False, color=color)
                if text_fields[0] == field else
                # Include footer but no header on last message
                await self.get_embed(ctx, fields=[self.EmbedField("_", field)], footer=footer, timestamp=timestamp, color=color)
                if text_fields[-1] == field else
                # No footer or header on middle message(s)
                await self.get_embed(ctx, fields=[self.EmbedField("_", field)], footer=False, timestamp=False, color=color)
                for field in text_fields]
        else:
            # Create normal embed with title and footer if text is not chunked
            embeds = [
                await self.get_embed(
                    ctx,
                    fields=[self.EmbedField(header, text_fields[0])],
                    footer=footer,
                    timestamp=timestamp,
                    color=color)
            ]

        # Return embed objects if desired
        if return_embeds:
            return embeds

        # Otherwise just send each embed as a message
        for embed in embeds:
            await ctx.send(embed=embed)

    async def read_send_file(self, ctx: commands.Context, path: str, *, encoding: str="utf-8") -> str:
        with open(path, "r", encoding=encoding) as f:
            return await self.send_text_message(ctx, f.read())

    def generate_hex_color_code(self, phrase: str, as_int: bool=True) -> int:
        phrase = str(phrase).encode()
        h = hashlib.blake2b(phrase, digest_size=3, key=b"vjemmie")
        if as_int:
            return int(h.hexdigest(), 16)
        return h.hexdigest()

    async def get_filename_extension_from_url(self, url: str) -> tuple:
        fname, extension = os.path.splitext(
            os.path.basename(urlsplit(url).path))

        if not extension:
            raise AttributeError("URL has no file extension")

        return fname, extension
