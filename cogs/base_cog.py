import discord
from discord.ext import commands
from typing import Iterable
from datetime import datetime


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
    
    async def send_log(self, msg: str, ctx: commands.Context=None) -> None:
        try:
            channel = self.bot.get_channel(self.log_channel_id)
            user_msg = f"{ctx.author.name}: {ctx.message.content}" if ctx else None
            await channel.send(f"{str(datetime.now())}: {msg}\n{user_msg}")
        except discord.Forbidden:
            print(f"Insufficient permissions for channel {self.log_channel_id}.")
        except discord.HTTPException:
            print(f"Failed to send message to channel {self.log_channel_id}.")

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