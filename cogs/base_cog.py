import discord
from discord.ext import commands
from typing import Iterable, Union
from datetime import datetime
import traceback
from cogs.admin_utils import is_not_blacklisted
from collections import namedtuple
import requests
import aiohttp

md_formats = ['asciidoc', 'autohotkey', 'bash',
            'coffeescript', 'cpp', 'cs', 'css',
            'diff', 'fix', 'glsl', 'ini', 'json',
            'md', 'ml', 'prolog', 'py', 'tex',
            'xl', 'xml']

EmbedField = namedtuple("EmbedField", "name value")

class BaseCog:
    IMAGE_CHANNEL_ID = 549649397420392567
    EmbedField = namedtuple("EmbedField", "name value")
    """
    Base Cog from which all other cogs are subclassed.
    """
    def __init__(self, bot: commands.Bot, log_channel_id: int) -> None:
        self.bot = bot
        self.log_channel_id = log_channel_id
        self.author_mention = "<@103890994440728576>"
        self._add_error_handlers()
        #self._add_checks()
        self.add_help_command()
    
    @property
    def cog_name(self) -> str:
        cog_name = self.__class__.__name__
        return cog_name if not cog_name.endswith("Cog") else cog_name[:-3]
    
    def add_help_command(self) -> None:
        IGNORE = ["reddit", "youtube", "weather", "cod"]
        command_name = self.cog_name.lower()
        if command_name != "base" and command_name not in IGNORE:
            cmd_coro = self._get_cog_commands
            cmd = commands.command(name=command_name)(cmd_coro)
            cmd.on_error = self._error_handler
            #self.bot.add_command(cmd())
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
        if isinstance(color, str):
            try:
                color_func = getattr(discord.Color, color)
            except:
                raise discord.DiscordException(f"Could not interpret {color}")
            else:
                return color_func()
        elif isinstance(color, int):
            return discord.Color(int)
        else:
            raise discord.DiscordException("Could not obtain color")

    async def get_embed(self,
                        ctx,
                        *,
                        title: str=None,
                        footer: bool=True,
                        fields: list=None,
                        content: str=None,
                        image_url: str=None,
                        color: Union[str, int]=None,
                        timestamp: bool=True) -> discord.Embed:
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

    async def send_log(self, msg: str, ctx: commands.Context=None) -> None:
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
            channel = self.bot.get_channel(self.log_channel_id)
            cause_of_error = f"\n\nMessage that caused error: {ctx.author.name}: {ctx.message.content}" if ctx else ""
            await channel.send(f"{msg}{cause_of_error}")
        except discord.Forbidden:
            print(f"Insufficient permissions for channel {self.log_channel_id}.")
        except discord.HTTPException:
            print(f"Failed to send message to channel {self.log_channel_id}.")

    def _add_error_handlers(self) -> None:
        for _attr in dir(self):
            try:
                # If subclasses call super().__init__ before instantiating its own instance variables,
                # getattr may raise exceptions. try/except retard-proofs it for myself.
                bot_command = getattr(self, _attr)
            except:
                pass
            else:
                if isinstance(bot_command, discord.ext.commands.core.Command):
                    # add check
                    if not hasattr(bot_command, "on_error"):
                        bot_command.on_error = self._error_handler

    async def _error_handler(self, ctx, error, *bugged_params) -> None:
        if bugged_params: # Sometimes two instances of self is passed in, totaling 4 args instead of 3
            ctx = error
            error = bugged_params[0]
        error_msg = error.args[0]
        if "The check functions" in error_msg: # lack of user privileges
            await ctx.send("Insufficient rights to perform command!")
        else:
            await self._unknown_error(ctx)

    async def _unknown_error(self, ctx):
        not_unknown = [
            "Command raised an exception",
            "MissingRequiredArgument",
            "BadArgument"
        ]
        ignore = []
        error_msg = traceback.format_exc()
        last_exception_line = error_msg.splitlines()[-1]
        if any(x in last_exception_line for x in not_unknown) and not any(x in last_exception_line for x in ignore):
            *_, user_error = last_exception_line.split(":")
            out_msg = f"**Error:** {user_error}"
        else:
            out_msg = "An unknown error occured"
        await ctx.send(out_msg) # Display error to user
        await self.send_log(error_msg, ctx) # Send entire exception traceback to log channel

    async def download_from_url(self, url: str) -> bytes: # TODO: FIX
        async with aiohttp.ClientSession() as session:
            r = await session.get(url)
            img = await r.read()
            return img

    async def upload_image_to_discord(self, image_url: str) -> discord.Message:
        channel = self.bot.get_channel(self.IMAGE_CHANNEL_ID)
        image = await self.download_from_url(image_url)
        *_, file_name = image_url.split("/")
        fname, ext = file_name.split(".", 1) # Fails if image_url is not an URL to a file
        msg = await channel.send(file=discord.File(image, file_name))
        return msg

    async def while_func_condition(self,
                                   func_condition,
                                   #condition,
                                   if_true: bool,
                                   coro,
                                   limit: int, 
                                   *args,
                                   **kwargs) -> None:
        raises = kwargs.get("raises", "Unknown error")
        n = 0
        rtn = await coro(*args)
        while func_condition(rtn) == if_true:
            rtn = await coro(*args)
            n += 1
            if n > limit:
                raise discord.DiscordException(raises)
        return rtn

    async def _get_cog_commands(self, ctx: commands.Context) -> None:
        """This command
        """
        _commands = sorted(
            [  # Get all public commands for the cog
                cmd for cmd in self.bot.commands
                if cmd.cog_name == self.__class__.__name__
                and not cmd.checks  # Ignore admin-only commands
            ],
            key=lambda cmd: cmd.name)
        _out_str = ""
        for command in _commands:
            cmd_name = command.name.ljust(20,"\xa0")
            #cmd_name = command.signature.ljust(35,"\xa0") # Considering using this instead
            _out_str += f"`!{cmd_name}:`\xa0\xa0\xa0\xa0{command.short_doc}\n"
        field = self.EmbedField(f"{self.cog_name} commands", _out_str)
        embed = await self.get_embed(ctx, fields=[field])
        await ctx.send(embed=embed)