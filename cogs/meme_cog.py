import discord
from discord.ext import commands
from cogs.base_cog import BaseCog

class MemeCog(BaseCog):
    """Various meme commands"""
    
    # TODO: Do something like: await send_text_message(ctx, await self.read_text_file())
    @commands.command(name="goodshit")
    async def goodshit(self, ctx: commands.Context) -> None:
        await self.read_send_file(ctx, "memes/txt/goodshit.txt")

    @commands.command(name="mason")
    async def mason(self, ctx: commands.Context) -> None:
        await self.read_send_file(ctx, "memes/txt/mason.txt")
    
    @commands.command()
    async def psio(self, ctx: commands.Context) -> None:
        await self.read_send_file(ctx, "memes/txt/psio.txt")

