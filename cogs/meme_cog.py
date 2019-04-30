import random

import discord
from discord.ext import commands

from cogs.base_cog import BaseCog


class MemeCog(BaseCog):
    """Text meme commands"""

    EMOJI = ":spaghetti:"
    
    def __init__(self, bot) -> None:
        super().__init__(bot)
        self.wordlist = []
    
    @commands.command(name="goodshit")
    async def goodshit(self, ctx: commands.Context) -> None:
        """👌👀👌👀👌👀👌👀👌👀"""
        await self.read_send_file(ctx, "memes/txt/goodshit.txt")

    @commands.command(name="mason")
    async def mason(self, ctx: commands.Context) -> None:
        "DOTA ALL STAR..."
        await self.read_send_file(ctx, "memes/txt/mason.txt")

    @commands.command(name="madara")
    async def madara(self, ctx: commands.Context) -> None:
        """Is there a character..."""
        await self.read_send_file(ctx, "memes/txt/madara.txt")

    @commands.command(name="goodmorning")
    async def goodmorning(self, ctx: commands.Context) -> None:
        if not self.wordlist:
            with open("memes/txt/6of12.txt", "r") as f:
                self.wordlist = f.read().splitlines()
        
        word = random.choice(self.wordlist)
        
        await ctx.send(f"Good morning to everyone apart from {word}s")
