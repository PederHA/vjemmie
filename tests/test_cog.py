import asyncio
import copy
import inspect
import traceback
import unittest
from contextlib import contextmanager
from unittest.mock import Mock

import discord
from discord.ext import commands

from cogs.base_cog import BaseCog
from utils.checks import owners_only
from utils.exceptions import CommandError


class TestError(Exception):
    pass


class TestCog(BaseCog):
    """Automated tests. Pretty shit"""
    
    DISABLE_HELP = True
    FAIL_MSG = "{cmd_name} {a_kw} FAIL ❌"
    PASS_MSG = "{cmd_name} {a_kw} PASS ✔️" 

    def __init__(self, bot: commands.Bot) -> None:
        super().__init__(bot)
        self.verbose = False
        self.pfix = self.bot.command_prefix
    
    @commands.command(name="verbose")
    async def toggle_verbose(self, ctx: commands.Context) -> None:
        self.verbose = not self.verbose
        await ctx.send(f"Test terminal output is now {'enabled' if self.verbose else 'disabled'}")
    
    @commands.command(name="run_tests", aliases=["runtest", "runtests", "tests"])
    @owners_only()
    async def run_tests(self, ctx: commands.Context) -> None:
        # Store test results
        passed = []
        failed = []

        # Temporarily patch ctx to disable message sending
        # while invoking bot commands
        with self.patch_ctx(ctx) as ctx:
            # Find tests
            for k in dir(self):
                if k.startswith("test_"):
                    coro = getattr(self, k)
                    if inspect.iscoroutinefunction(coro):
                        try:
                            await coro(ctx)
                        except:
                            failed.append(k)
                        else:
                            passed.append(k)
            print("Tests completed!")

        # Format results
        passed_fmt = "\n".join(passed)
        failed_fmt = "\n".join(failed)
        
        if not failed:
            result = "All tests passed!"
        elif not passed:
            result = "All tests failed"
        else:
            result = f"Passed:\n{passed_fmt}\n\nFailed:\n{failed_fmt}\n"
        await self.send_text_message(result, ctx)

    @contextmanager        
    def patch_ctx(self, ctx: commands.Context) -> commands.Context:
        """Patches the `send()` method of a 
        `discord.ext.commands.Context` object with a dummy method
        that disables message sending while tests are running."""
        async def new_send(*args, **kwargs):
            pass
        original_ctx = copy.copy(ctx)
        try:
            ctx.send = new_send
            yield ctx
        finally:
            ctx = original_ctx

    async def _do_test(self, coro_or_cmd, *args, **kwargs) -> None:
        # Pop ctx
        ctx = kwargs.pop("ctx", None)
        
        # Object to test equality of result with
        assertion = kwargs.pop("assertion", object())
        
        # Assert type of result instead of value
        assert_type = kwargs.pop("assert_type", False)
        
        # same as TestCase.assertRaises
        raises = kwargs.pop("raises", None)

        # Get name of command or coro, str formatted args and str formatted kwargs
        cmd_name, _args, _kwargs = await self._get_test_attrs(coro_or_cmd, *args, **kwargs)
        
        # Show args & kwargs if verbose is enabled
        a_kw = f"{_args}, {_kwargs}" if self.verbose else ""

        passed = False
        try:
            if ctx:
                r = await ctx.invoke(coro_or_cmd, *args, **kwargs)
            else:
                r = await coro_or_cmd(*args, **kwargs)
            if type(assertion) != object:
                if assert_type:
                    assert type(r) == assertion
                else:
                    assert r == assertion
        except AssertionError:
            await self._format_assertion_error(assertion, assert_type)
        except Exception as e:
            passed = await self._handle_exc(e, raises)
        else:
            passed = True
        finally:
            if passed:
                msg = self.PASS_MSG
            else:
                msg = self.FAIL_MSG
            msg = msg.format(cmd_name=cmd_name, a_kw=a_kw)
            print(msg)
            if not passed:
                raise TestError(msg)
    
    async def _format_assertion_error(self, assertion, assert_type) -> None:
        print(traceback.format_exc())
        if type(assertion) != object:
            if assert_type:
                print(f"type(r) == {type(r)}", end=", ")
            else:
                print(f"r == {r}", end=", ")
            print(f"assertion == {assertion}")
    
    async def _handle_exc(self, exc, raises) -> bool:
        passed = False
        if raises:
            try:
                assert type(exc) == raises
            except:
                pass
            else:
                passed = True
        if not passed:
            print(traceback.format_exc())
        return passed
    
    async def _get_test_attrs(self, coro_or_cmd, *args, **kwargs) -> tuple:
        # Get coroutine or command's name
        try:
            coro_or_cmd_name = coro_or_cmd.__func__.__name__
        except:
            coro_or_cmd_name = f"{self.pfix}{coro_or_cmd.name}"
        
        # String formatted args, kwargs
        _args = f"\t{args}" if args else ""
        _kwargs = f"\t{kwargs}" if kwargs else ""

        return coro_or_cmd_name, _args, _kwargs      
    
    async def do_test_coro(self, coro, *args, **kwargs) -> None:
        return await self._do_test(coro, *args, **kwargs)
 
    async def do_test_command(self, ctx: commands.Context, cmd: commands.Command, *args, **kwargs) -> None:    
        if isinstance(cmd, str):
            cmd = self.bot.get_command(cmd)
        if not cmd:
            raise TypeError("Command must be name of command or discord.ext.commands.Command object!")
        return await self._do_test(cmd, *args, **kwargs, ctx=ctx)    
    
    #########################################
    #####             TESTS             #####
    #########################################

    # AdminCog
    async def test_admincog_change_activity(self, ctx: commands.Context) -> None:
        cmd = self.bot.get_command("change_activity")
        await self.do_test_command(ctx, cmd, "test activity")
        await asyncio.sleep(0.5)
        # Reset to default activity
        await ctx.invoke(cmd)
    
    async def test_admincog_serverlist(self, ctx: commands.Context) -> None:
        await self.do_test_command(ctx, "serverlist")    
    
    # AvatarCog
    async def test_avatarcog_fuckup(self, ctx: commands.Context) -> None:
        """AvatarCog command where `template_overlay==False`"""
        await self.do_test_command(ctx, "fuckup")
    
    async def test_avatarcog_mlady(self, ctx: commands.Context) -> None:
        """AvatarCog command where `template_overlay==True`"""
        await self.do_test_command(ctx, "mlady")    
    
    # FunCog
    async def test_funcog_roll(self, ctx: commands.Context) -> None:
        await self.do_test_command(ctx, "roll", 1, 100)
        await self.do_test_command(ctx, "roll", "foo", "bar", raises=CommandError)

    async def test_funcog_random(self, ctx: commands.Context) -> None:
        await self.do_test_command(ctx, "random", "Jeff", "Steve", "Travis", "Hugo")

    async def test_funcog_braille(self, ctx: commands.Context) -> None:
        await self.do_test_command(ctx, "braille", "testing braille command")

    # PUBGCog
    async def test_pubgcog_drop(self, ctx: commands.Context) -> None:
        await self.do_test_command(ctx, "drop", "erangel", "hot")

    async def test_pubgcog_crate(self, ctx: commands.Context) -> None:
        await self.do_test_command(ctx, "crate")

    # RedditCog
    async def test_redditcog_meme(self, ctx: commands.Context) -> None:
        await self.do_test_command(ctx, "meme")

    async def test_redditcog_reddit(self, ctx: commands.Context) -> None:
        await self.do_test_command(ctx, "reddit", "python")

    async def test_redditcog_rsettings(self, ctx: commands.Context) -> None:
        await self.do_test_command(ctx, "rsettings")

    async def test_redditcog_rsort(self, ctx: commands.Context) -> None:
        cmd = self.bot.get_command("rsort")
        await self.do_test_command(ctx, cmd)
        await ctx.invoke(cmd)
    
    async def test_redditcog_rtime(self, ctx: commands.Context) -> None:
        await self.do_test_command(ctx, "rtime")
    
    async def test_redditcog_subs(self, ctx: commands.Context) -> None:
        await self.do_test_command(ctx, "subs")
    
    # SoundCog
    async def test_soundcog_connect(self, ctx: commands.Context) -> None:
        await self.do_test_command(ctx, "connect")

    async def test_soundcog_play(self, ctx: commands.Context) -> None:
        await self.do_test_command(ctx, "play", "dota")
    
    async def test_soundcog_queue(self, ctx: commands.Context) -> None:
        pass
    
    async def test_soundcog_stop(self, ctx: commands.Context) -> None:
        await self.do_test_command(ctx, "stop")
    
    # StatsCog
    async def test_statscog_uptime(self, ctx: commands.Context) -> None:
        await self.do_test_command(ctx, "uptime")
        await self.do_test_command(ctx, "uptime", rtn=True, assertion=str, assert_type=True)
    
    async def test_statscog_changelog(self, ctx: commands.Context) -> None:
        await self.do_test_command(ctx, "changelog", rtn_type=list, assertion=list, assert_type=True)
    
    # ImageCog    
    async def _test_deepfry(self, ctx: commands.Context) -> None:
        # Get !deepfry command
        deepfry_cmd = self.bot.get_command("deepfry")
        
        url = "https://cdn.discordapp.com/attachments/560503336013529091/566615384808095754/Gfw036Q.png"
        
        # Test command with URL argument
        print(f"Testing {self.pfix}deepfry with URL.")
        await self.do_test_command(ctx, deepfry_cmd, "-url", url)        

        # Sleep between image uploads to be nice to Discord
        await asyncio.sleep(5)
   
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
            state=Mock(http=None)
            )
        
        # Attach attachment to ctx.message
        ctx.message.attachments.append(attachment)
        
        # Test with message attachment
        print(f"Testing {self.pfix}deepfry with attachment.")
        await self.do_test_command(ctx, deepfry_cmd)
