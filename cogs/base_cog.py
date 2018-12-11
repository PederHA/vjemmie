import discord
from discord.ext import commands
from typing import Iterable

class BaseCog:
    """
    Base Cog from which all other cogs are subclassed.
    """
    def __init__(self, bot: commands.Bot, log_channel_id: int) -> None:
        self.bot = bot
        self.log_channel_id = log_channel_id
    
    async def send_log(self, msg: str) -> None:
        try:
            channel = self.bot.get_channel(self.log_channel_id)
            await channel.send(msg)
        except discord.Forbidden:
            print(f"Insufficient permissions for channel {self.log_channel_id}.")
        except discord.HTTPException:
            print(f"Failed to send message to channel {self.log_channel_id}.")

    async def format_output(self, items: Iterable, item_type: str=None, header: bool=False, enum: bool=False) -> str:
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
        """

        output = "```"
        if header and item_type is not None:
            output += f"Available {item_type}:\n\n"
        for i, item in enumerate(items, 1):
            if enum:
                idx = f"{i}. "
            else:
                idx = ""
            output += f"{idx}{item}\n"
        else:
            output += "```"
        return output

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