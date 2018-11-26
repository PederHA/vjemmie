from discord.ext import commands
import discord
from ext_module import ExtModule
import random
import os
from cogs.db_cog import DatabaseHandler
from cogs.base_cog import BaseCog

class PFMCog(BaseCog):
    """
    PFM Memes Cog
    """
    def __init__(self, bot: commands.Bot, log_channel_id: int=None) -> None:
        super().__init__(bot, log_channel_id)
        self.image_file_types = ["png", "jpeg", "jpg", "gif", "gifv"]
        self.db = DatabaseHandler("memes/pfm_memes.db")

    @commands.command(name="testdb")
    async def testdb(self, ctx: commands.Context, *args):
        await self.db.get_memes("nezgroul", ctx, args)    

    @commands.command(aliases=["groul", "boomkin", "rapist", "gypsy"])
    async def nezgroul(self, ctx: commands.Context, *args):
        await self.db.get_memes("nezgroul", ctx, args)

    @commands.command()
    async def pfm(self, ctx: commands.Context, *args):
        await self.db.get_memes("pfm", ctx, args)

    @commands.command()
    async def pman(self, ctx: commands.Context, *args):
        await self.db.get_memes("pman", ctx, args)

    @commands.command()
    async def verdisha(self, ctx: commands.Context, *args):
        await self.db.get_memes("verdisha", ctx, args)

    @commands.command()
    async def preach(self, ctx: commands.Context, *args):
        await self.db.get_memes("verdisha", ctx, args)

    @commands.command()
    async def hugo(self, ctx: commands.Context, *args):
        await self.db.get_memes("hugo", ctx, args)

    @commands.command(aliases=["brokenlenny"])
    async def lenny(self, ctx: commands.Context, *args):
        await self.db.get_memes("brokenlenny", ctx, args)

    @commands.command(aliases=["pogboom", "swagforsteve"])
    async def steve(self, ctx: commands.Context, *args):
        await self.db.get_memes("steve", ctx, args)

    @commands.command()
    async def yendis(self, ctx: commands.Context, *args):
        await self.db.get_memes("yendis", ctx, args)

    @commands.command(aliases=["calum", "swansea", "heroin"])
    async def khunee(self, ctx: commands.Context, *args):
        await self.db.get_memes("khunee", ctx, args)

    @commands.command(aliases=["dynei"])
    async def razjar(self, ctx: commands.Context, *args):
        await self.db.get_memes("razjar", ctx, args)

    @commands.command(aliases=["rank2"])
    async def hoob(self, ctx: commands.Context, *args):
        await self.db.get_memes("hoob", ctx, args)

    @commands.command(aliases=["turk", "kebab"])
    async def huya(self, ctx: commands.Context, *args):
        await self.db.get_memes("huya", ctx, args)

    @commands.command(aliases=["fidgetspinner", "420"])
    async def notey(self, ctx: commands.Context, *args):
        await self.db.get_memes("notey", ctx, args)

    @commands.command(aliases=["emil", "pedo", "pedorad", "email"])
    async def rad(self, ctx: commands.Context, *args):
        await self.db.get_memes("rad", ctx, args)

    @commands.command(aliases=["travis", "triggered"])
    async def truffles(self, ctx: commands.Context, *args):
        await self.db.get_memes("travis", ctx, args)

    @commands.command(aliases=["zizzka", "janis"])
    async def zizzkka(self, ctx: commands.Context, *args):
        await self.db.get_memes("zizzkka", ctx, args)

    @commands.command(aliases=["gays"])
    async def frosty(self, ctx: commands.Context, *args):
        await self.db.get_memes("frosty", ctx, args)

    @commands.command(aliases=["daevi"])
    async def tekk(self, ctx: commands.Context, *args):
        await self.db.get_memes("tekk", ctx, args)

    @commands.command(aliases=["liam", "fattydoobies", "doobieshank"])
    async def doobies(self, ctx: commands.Context, *args):
        await self.db.get_memes("doobies", ctx, args)

    @commands.command()
    async def psio(self, ctx: commands.Context, *args):
        with open('memes/psio.txt', 'r', encoding='utf8') as meme:
            await ctx.send(meme.read())
    
    @commands.command()
    async def goodshit(self, ctx: commands.Context, *args):
        with open('memes/goodshit.txt', 'r', encoding='utf8') as meme:
            await ctx.send(meme.read())

    @commands.command(name="memes", alias=["list_memes"])
    async def list_memes(self, ctx: commands.Context, *args):
        await self.db.get_memes("list_memes", ctx, ("list",))