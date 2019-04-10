import discord
from discord.ext import commands
from cogs.base_cog import BaseCog, EmbedField

class MemeCog(BaseCog):
    """Text meme commands"""

    @commands.command(name="goodshit")
    async def goodshit(self, ctx: commands.Context) -> None:
        await self.read_send_file(ctx, "memes/txt/goodshit.txt")

    @commands.command(name="mason")
    async def mason(self, ctx: commands.Context) -> None:
        await self.read_send_file(ctx, "memes/txt/mason.txt")
