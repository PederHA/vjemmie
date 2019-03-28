from discord.ext import commands
import discord
from ext_module import ExtModule
import random
import os
from cogs.db_cog import DatabaseHandler
from cogs.base_cog import BaseCog
from ext.checks import is_pfm

class PFMCog(BaseCog):
    """
    PFM Memes Cog
    """
    image_file_types = ["png", "jpeg", "jpg", "gif", "gifv"] # UNUSED LOL
    db = DatabaseHandler("memes/pfm_memes.db")

    @commands.command(name="testdb")
    @is_pfm()
    async def testdb(self, ctx: commands.Context, *args):
        await self.db.get_memes("nezgroul", ctx, args)    

    @commands.command(aliases=["groul", "boomkin", "rapist", "gypsy"])
    @is_pfm()
    async def nezgroul(self, ctx: commands.Context, *args):
        await self.db.get_memes("nezgroul", ctx, args)

    @commands.command(name="pfmmeme")
    @is_pfm()
    async def pfm(self, ctx: commands.Context, *args):
        await self.db.get_memes("pfm", ctx, args)

    @commands.command()
    @is_pfm()
    async def pman(self, ctx: commands.Context, *args):
        await self.db.get_memes("pman", ctx, args)

    @commands.command()
    @is_pfm()
    async def verdisha(self, ctx: commands.Context, *args):
        await self.db.get_memes("verdisha", ctx, args)

    @commands.command()
    @is_pfm()
    async def preach(self, ctx: commands.Context, *args):
        await self.db.get_memes("verdisha", ctx, args)

    @commands.command()
    @is_pfm()
    async def hugo(self, ctx: commands.Context, *args):
        await self.db.get_memes("hugo", ctx, args)

    @commands.command(aliases=["brokenlenny"])
    @is_pfm()
    async def lenny(self, ctx: commands.Context, *args):
        await self.db.get_memes("brokenlenny", ctx, args)

    @commands.command(aliases=["pogboom", "swagforsteve"])
    @is_pfm()
    async def steve(self, ctx: commands.Context, *args):
        await self.db.get_memes("steve", ctx, args)

    @commands.command()
    @is_pfm()
    async def yendis(self, ctx: commands.Context, *args):
        await self.db.get_memes("yendis", ctx, args)

    @commands.command(aliases=["calum", "swansea", "heroin"])
    @is_pfm()
    async def khunee(self, ctx: commands.Context, *args):
        await self.db.get_memes("khunee", ctx, args)

    @commands.command(aliases=["dynei"])
    @is_pfm()
    async def razjar(self, ctx: commands.Context, *args):
        await self.db.get_memes("razjar", ctx, args)

    @commands.command(aliases=["rank2"])
    @is_pfm()
    async def hoob(self, ctx: commands.Context, *args):
        await self.db.get_memes("hoob", ctx, args)

    @commands.command(aliases=["turk", "kebab"])
    @is_pfm()
    async def huya(self, ctx: commands.Context, *args):
        await self.db.get_memes("huya", ctx, args)

    @commands.command(aliases=["fidgetspinner", "420"])
    @is_pfm()
    async def notey(self, ctx: commands.Context, *args):
        await self.db.get_memes("notey", ctx, args)

    @commands.command(aliases=["emil", "pedo", "pedorad", "email"])
    @is_pfm()
    async def rad(self, ctx: commands.Context, *args):
        await self.db.get_memes("rad", ctx, args)

    @commands.command(aliases=["travis", "triggered"])
    @is_pfm()
    async def truffles(self, ctx: commands.Context, *args):
        await self.db.get_memes("travis", ctx, args)

    @commands.command(aliases=["zizzka", "janis"])
    @is_pfm()
    async def zizzkka(self, ctx: commands.Context, *args):
        await self.db.get_memes("zizzkka", ctx, args)

    @commands.command(aliases=["gays"])
    @is_pfm()
    async def frosty(self, ctx: commands.Context, *args):
        await self.db.get_memes("frosty", ctx, args)

    @commands.command(aliases=["daevi"])
    @is_pfm()
    async def tekk(self, ctx: commands.Context, *args):
        await self.db.get_memes("tekk", ctx, args)

    @commands.command(aliases=["liam", "fattydoobies", "doobieshank"])
    @is_pfm()
    async def doobies(self, ctx: commands.Context, *args):
        await self.db.get_memes("doobies", ctx, args)

    @commands.command(name="memes", alias=["list_memes"])
    @is_pfm()
    async def list_memes(self, ctx: commands.Context, *args):
        await self.db.get_memes("list_memes", ctx, ("list",))

