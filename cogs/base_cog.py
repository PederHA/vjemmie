import discord
from discord.ext import commands

class BaseCog:
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