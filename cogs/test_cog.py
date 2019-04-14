from discord.ext import commands
import discord
from cogs.base_cog import BaseCog
import asyncio


class TestCog(BaseCog):
    """Automated tests. Pretty shit"""
    
    DISABLE_HELP = True

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

    async def _do_test(self, coro_or_cmd, *args, **kwargs) -> None:
        cmd_n, raise_exc, _args, _kwargs = await self._get_test_attrs(coro_or_cmd, *args, **kwargs)
        ctx = kwargs.pop("ctx", None)
        assert_true = kwargs.pop("assert_true", None)
        
        if self.verbose:
            print(f"""testing "{cmd_n}" with args: {_args}\tkwargs: {_kwargs}""", end="")
            if ctx and ctx.message.attachments:
                print(f"and attachment {ctx.message.attachments[0].url}")
            else:
                print()
        
        try:
            if ctx:
                await ctx.invoke(coro_or_cmd, *args, **kwargs)
            else:
                assert await coro_or_cmd(*args, **kwargs)
        except:
            if raise_exc:
                raise
            print(f""""{cmd_n}" failed on {_args} {_kwargs}""")   
        else:
            if self.verbose:
                print(f""""{cmd_n}({_args}, {_kwargs})" passed! OK""")           
    
    async def _get_test_attrs(self, coro_or_cmd, *args, **kwargs) -> tuple:
        # Get coroutine or command's name
        try:
            coro_or_cmd_name = coro_or_cmd.__func__.__name__
        except:
            coro_or_cmd_name = coro_or_cmd.name
        
        # Whether to raise test assertion errors or not
        raise_exc = kwargs.pop("raise_exc", False)        
        
        # String formatted args, kwargs
        _args = f"\t{args}" if args else ""
        _kwargs = f"\t{kwargs}" if kwargs else ""

        return coro_or_cmd_name, raise_exc, _args, _kwargs      
    
    async def test_coro_true(self, coro, *args, **kwargs) -> None:
        return await self._do_test(coro, *args, **kwargs)
 
    async def test_command(self, ctx: commands.Context, cmd: commands.Command, *args, **kwargs) -> None:    
        return await self._do_test(cmd, *args, **kwargs, ctx=ctx)    
    
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
            await self.test_coro_true(self.is_img_url, url)
  
    @commands.command(name="test_deepfry")
    async def test_deepfry(self, ctx: commands.Context) -> None:
        # Get !deepfry command
        deepfry_cmd = self.bot.get_command("deepfry")
        
        url = "https://cdn.discordapp.com/attachments/560503336013529091/566615384808095754/Gfw036Q.png"
        
        # Test command with URL argument
        print("Testing !deepfry with URL.")
        await self.test_command(ctx, deepfry_cmd, url)        

        await asyncio.sleep(5)

        # Create attachment object
        class FakeState:
            http = None
            def __init__(self, *args, **kwargs) -> None:
                pass   
        
        attachment = discord.Attachment(
            data={
                "filename" : "Gfw036Q.png",
                "height" : 715,
                "id": 666,
                "proxy_url": "https://media.discordapp.net/attachments/560503336013529091/566615384808095754/Gfw036Q.png",
                "size": 216770,
                "url": url,
                "width": 720
            },
            state=FakeState()
            )
        
        # Attach attachment to ctx.message
        ctx.message.attachments.append(attachment)
        
        # Test with message attachment
        print("Testing !deepfry with attachment.")
        await self.test_command(ctx, deepfry_cmd)