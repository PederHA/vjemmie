import discord
from discord.ext import commands
from typing import Iterable
from datetime import datetime
import traceback


md_formats = ['asciidoc', 'autohotkey', 'bash', 
            'coffeescript', 'cpp', 'cs', 'css', 
            'diff', 'fix', 'glsl', 'ini', 'json', 
            'md', 'ml', 'prolog', 'py', 'tex', 
            'xl', 'xml']

class BaseCog:
    """
    Base Cog from which all other cogs are subclassed.
    """
    def __init__(self, bot: commands.Bot, log_channel_id: int) -> None:
        self.bot = bot
        self.log_channel_id = log_channel_id
        self.author_mention = "<@103890994440728576>"
        self._add_error_handlers()

    async def format_output(self, items: Iterable, *, formatting: str="", item_type: str=None, header: bool=False, enum: bool=False) -> str:
        """
        Creates a multi-line codeblock in markdown formatting
        listing items in iterable `items` on separate lines.

        Args:
            items (Iterable): Iterable of items to be represented
            item_type (str): (optional) Description of items in iterable. Default: None
            header (bool): (optional) Generates header on first line out returned str. Default: False
            enum: (optional) Generates index next to each item listing. Default: False
        
        Returns:
            output (str): Markdown formatted code block listing items in iterable, 1 per line.

        Example:
            >>>format_output(["foo", "bar", "baz"], "generic items", header=True)
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
        if header and item_type is not None:
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
        """
        This method should be renamed, or I'll need to make a separate `send_error_log` method.
        Either way, that's not something that I will do right away.
        """
        try:
            channel = self.bot.get_channel(self.log_channel_id)
            user_msg = f"{ctx.author.name}: {ctx.message.content}" if ctx else None
            await channel.send(f"{str(datetime.now())}\n{msg}\n\nMessage that caused error: {user_msg}")
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
                    if not hasattr(bot_command, "on_error"):
                        bot_command.on_error = self._error_handler     
    
    async def _error_handler(self, ctx, error, *bugged_params) -> None:
        if bugged_params: # Sometimes two instances of self is passed in, totaling 4 args instead of 3
            ctx = error
            error = bugged_params[0]
        error_msg = error.args[0]
        if "The check functions" in error_msg:
            await ctx.send("Insufficient rights to perform command!")
        else:
            await self.unknown_error(ctx)

    async def unknown_error(self, ctx, error=None, with_traceback=True):
        if error:
            with_traceback = False
        if with_traceback:
            error_msg = traceback.format_exc()
        else:
            if isinstance(error, discord.ext.commands.errors.CommandInvokeError):
                error_msg = str(error.args)
            else:
                error_msg = str(error)
        await ctx.send("An unknown error occured")
        await self.send_log(error_msg, ctx)

