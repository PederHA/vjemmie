from discord.ext import commands
import discord
import pytest
from cogs.base_cog import BaseCog

class TestCog(BaseCog):
    
    @pytest.mark.asyncio
    async def test_reddit_add_sub(self):
        channel = self.bot.get_channel(self.LOG_CHANNEL_ID)
        cmd = await self.bot.get_command("add_sub")
        with pytest.raises(discord.DiscordException):
            await channel.invoke(cmd, "comedyheaven")