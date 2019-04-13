from discord.ext import commands
import discord
from cogs.base_cog import BaseCog
import asyncio


class TestCog(BaseCog):
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__(bot)
        self.verbose = False
    
    @commands.command(name="verbose")
    async def toggle_verbose(self, ctx: commands.Context) -> None:
        self.verbose = not self.verbose
        await ctx.send(f"Test terminal output is now {'enabled' if self.verbose else 'disabled'}")
    
    @commands.command(name="run_tests", aliases=["test"])
    async def run_tests(self, ctx: commands.Context) -> None:
        for command in self.get_commands():
            if command.name in ["run_tests", "verbose"]:
                continue
            await ctx.invoke(command)
    
    async def _do_test(self, coro, *args, **kwargs) -> None:
        # Get coroutine function's name
        coro_n = coro.__func__.__name__
        
        # Whether to raise test assertion errors or not
        raise_exc = kwargs.pop("raise_exc", False)
        
        args = f"\t{args}" if args else ""
        kwargs = f"\t{kwargs}" if kwargs else ""         
        
        if self.verbose:
            print(f"""testing "{coro_n}" with args: {args}\tkwargs: {kwargs}""")
        
        try:
            assert await coro(*args, **kwargs)
        except:
            if raise_exc:
                raise
  
            print(f""""{coro_n}" failed on {args} {kwargs}""")
        else:
            if self.verbose:
                print(f""""{coro_n}({args}, {kwargs})" passed! OK""")    
    
    #########################################
    #####             TESTS             #####
    #########################################

    @commands.command(name="test_is_img_url")
    async def test_is_img_url(self, ctx: commands.Context) -> None:
        urls = [
            "https://cdn.discordapp.com/avatars/103890994440728576/aab962dd36a3a9ce906ce06729dd6619.webp?size=1024",
            "https://cdn.discordapp.com/attachments/549649397420392567/566333674640113684/deepfried.jpg",
            "https://i.imgur.com/Gfw036Q.png",
            "https://i.imgur.com/Gfw036Q.PNG",
            "https://i.imgur.com/Gfw036Q.png?yeboi=True",
            "https://cdn.discordapp.com/attachments/348610981204590593/566394515347341312/caust.PNG"
        ]
        
        for url in urls:
            await self._do_test(self.is_img_url, url)


