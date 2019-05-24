"""Very simple testing suite for the bot's commands that came about due to my
impatience for getting tests up and running, but being unwilling to put in the
effort of researching how to integrate discord commands into existing testing frameworks.
"""
import asyncio
import copy
import inspect
import traceback
import operator
from itertools import cycle
from contextlib import contextmanager
from unittest.mock import Mock
from functools import wraps, partial
from typing import Coroutine, Awaitable, ContextManager, Any, TypeVar, Callable

import discord
from discord.ext import commands

from cogs.base_cog import BaseCog
from utils.checks import owners_only, test_server_cmd
from utils.exceptions import CommandError
from utils.messaging import wait_for_user_reply

SENTINEL = object() # Shouldn't strictly be called "sentinel", but it's not a None-value either...


class TestError(Exception):
    pass


def decorator_factory(attr_k: str, attr_v: Any=SENTINEL) -> Any: # Callable[[Any], Awaitable[[Any], Any]] IDK if this is correct, so we're going with Any
    """Creates a decorator that sets a given attribute 
    on an awaitable object.
    
    Parameters
    ----------
    attr_k : str
        Name of attribute
    attr_v : Any, optional
        Value of attribute, default SENTINEL
    """
    if attr_v is SENTINEL:
        attr_v = True
    def outer(f: Awaitable) -> Awaitable:
        setattr(f, attr_k, attr_v)
        @wraps(f)
        async def wrapper(*args, **kwargs):
            return await f(*args, **kwargs)
        return wrapper
    return outer


# Up/Downloads data to/from internet
network_io = decorator_factory("network_io")

# Uploads images to Discord
discord_io = decorator_factory("discord_io")

# Requires cmd invoker to be in a voice channel
voice = decorator_factory("voice")


class TestCog(BaseCog):
    """Automated tests. Pretty shit"""

    DISABLE_HELP = True
    FAIL_MSG = "{cmd_name} {a_kw} ❌"
    PASS_MSG = "{cmd_name} {a_kw} ✔️"

    def __init__(self, bot: commands.Bot) -> None:
        super().__init__(bot)
        self.pfix = self.bot.command_prefix
        self.verbose = True
        self.msg_enabled = False
        self.network_io_enabled = False # Enables commands such as: !meme, !reddit get, !twitter add
        self.discord_io_enabled = False # Enables commands such as: !fuckup, !mlady

    @commands.command(name="tverbose", aliases=["terminal_verbose"])
    async def toggle_terminal_verbose(self, ctx: commands.Context) -> None:
        return await self._toggle_attr(ctx, "verbose", "Test terminal output")

    @commands.command(name="verbose")
    async def toggle_message_send(self, ctx: commands.Context) -> None:
        return await self._toggle_attr(
            ctx,
            "msg_enabled",
            "Message sending",
            addendum="Be aware that Discord rate limits apply!")

    @commands.command(name="network_io", aliases=["io"])
    async def toggle_network_io(self, ctx: commands.Context) -> None:
        await self._toggle_attr(
            ctx, "network_io_enabled", description="Network IO-bound commands")

    @commands.command(name="discord_io", aliases=["dio"])
    async def toggle_discord_io(self, ctx: commands.Context) -> None:
        await self._toggle_attr(
            ctx, "discord_io_enabled", description="Discord IO-bound commands")

    async def _toggle_attr(self, ctx, attr: str, description: str, addendum: str=None, addendum_on_false: bool=False) -> None:
        # Toggle attr
        state = getattr(self, attr)
        new_state = not state
        setattr(self, attr, new_state)

        # Get string representation of attr state
        status = "enabled" if new_state else "disabled"

        # Generate addendum if passed in
        op = operator.not_ if addendum_on_false else operator.truth
        addendum = addendum if op(attr) and addendum else ""

        await ctx.send(f"{description} is now **{status}**! {addendum}")

    @commands.command(name="run_tests", aliases=["runtest", "runtests", "tests"])
    @owners_only()
    @test_server_cmd()
    async def run_tests(self, ctx: commands.Context) -> None:
        if not ctx.message.author.voice:
            msg = ("Not connected to a voice channel! "
            "You must be in a voice channel to run all tests.\n"
            "Are you sure you want to proceed with incomplete testing?")
            if await wait_for_user_reply(self.bot, ctx, msg):
                await ctx.send(
                    "Proceeding with incomplete testing!\n"
                    "**NOTE:** In order to run all tests you must be connected to a voice channel!")
            else:
                return await ctx.send("Aborting.")

        # Store test results
        passed = []
        failed = []

        # Temporarily patch ctx to disable message sending while invoking bot commands
        with self.patch_ctx(ctx) as ctx:
            # Find tests
            for k in dir(self):
                if k.startswith("test_"):
                    coro = getattr(self, k)
                    if not self.determine_run_coro(coro, ctx):
                        continue
                    if inspect.iscoroutinefunction(coro):
                        try:
                            await coro(ctx)
                        except:
                            failed.append(k)
                        else:
                            passed.append(k)
            await self._post_tests_cleanup(ctx)
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

    def determine_run_coro(self, coro, ctx: commands.Context, skip_network_io: bool) -> bool:
        """Checks if certain conditions are met, in order to determine
        if coroutine should be tested."""
        if not self.network_io_enabled and hasattr(coro, "network_io"):
            return False
        elif not self.discord_io_enabled and hasattr(coro, "discord_io"):
            return False
        elif not ctx.message.author.voice and hasattr(coro, "voice"):
            return False
        else:
            return True

    async def _post_tests_cleanup(self, ctx) -> None:
        """Calls methods required for cleanup after running tests."""
        # Nothing here for now
        pass

    @contextmanager
    def patch_ctx(self, ctx: commands.Context) -> ContextManager[commands.Context]:
        """Patches the `send()` method of a 
        `discord.ext.commands.Context` object with a dummy method
        that disables message sending while tests are running."""
        async def new_send(*args, **kwargs):
            pass
        new_send.testing = True

        original_ctx = copy.copy(ctx)
        try:
            enabled = self.msg_enabled
            if not enabled:
                # Patch ctx.send with dummy method
                ctx.send = new_send
                yield ctx
            else:
                yield ctx
        finally:
            ctx = original_ctx

    async def _do_test(self, coro_or_cmd, *args, **kwargs) -> None:
        # Pop ctx
        ctx = kwargs.pop("ctx", None)

        # Object to test equality of result with
        assertion = kwargs.pop("assertion", SENTINEL)

        # Assert type of result instead of value
        assert_type = kwargs.pop("assert_type", False)

        # same as TestCase.assertRaises
        raises = kwargs.pop("raises", None)

        # Get name of command or coro, str formatted args and str formatted kwargs
        cmd_name, _args, _kwargs = await self._get_test_attrs(coro_or_cmd, *args, **kwargs)

        # Show args & kwargs if verbose is enabled
        a_kw = f"{_args} {_kwargs}" if self.verbose else ""

        passed = False
        try:
            if ctx:
                r = await ctx.invoke(coro_or_cmd, *args, **kwargs)
            else:
                r = await coro_or_cmd(*args, **kwargs)
            if assertion is not SENTINEL:
                if assert_type:
                    assert type(r) == assertion
                else:
                    assert r == assertion
        except AssertionError:
            await self._format_assertion_error(cmd_name, assertion, assert_type)
        except Exception as e:
            passed = await self._handle_exc(cmd_name, e, raises)
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

    async def _format_assertion_error(self, cmd_name, assertion, assert_type) -> None:
        await self.log_test_error(cmd_name)
        if assertion is not SENTINEL:
            if assert_type:
                print(f"type(r) == {type(r)}", end=", ")
            else:
                print(f"r == {r}", end=", ")
            print(f"assertion == {assertion}")

    async def _handle_exc(self, cmd_name, exc, raises) -> bool:
        passed = False
        if raises:
            try:
                assert type(exc) == raises
            except:
                pass
            else:
                passed = True
        if not passed:
            await self.log_test_error(cmd_name)
        return passed

    async def log_test_error(self, cmd_name) -> None:
        exc_info = traceback.format_exc()
        with open(f"tests/logs/{cmd_name}.txt", "w") as f:
            f.write(exc_info)
        if self.verbose:
            print(exc_info)

    async def _get_test_attrs(self, coro_or_cmd, *args, **kwargs) -> tuple:
        # Get coroutine or command's name
        try:
            coro_or_cmd_name = coro_or_cmd.__func__.__name__
        except:
            coro_or_cmd_name = f"{self.pfix}{coro_or_cmd.qualified_name}"

        # String formatted args, kwargs
        _args = f"  {' '.join([repr(arg) for arg in args])}" if args else ""
        _kwargs = f"\t{', '.join([f'{k}={v}' for k, v in kwargs.items()])}" if kwargs else ""

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

    @discord_io
    async def test_admincog_serverlist(self, ctx: commands.Context) -> None:
        await self.do_test_command(ctx, "serverlist")

    # AvatarCog
    @discord_io
    async def test_avatarcog_fuckup(self, ctx: commands.Context) -> None:
        """AvatarCog command where `template_overlay==False`"""
        await self.do_test_command(ctx, "fuckup")

    @discord_io
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

    @voice
    async def test_pubgcog_crate(self, ctx: commands.Context) -> None:
        await self.do_test_command(ctx, "crate")
        await self.do_test_command(ctx, "crate", "c", raises=CommandError)

    # RedditCog
    @network_io
    async def test_redditcog_meme(self, ctx: commands.Context) -> None:
        await self.do_test_command(ctx, "meme")

    @network_io
    async def test_redditcog_get(self, ctx: commands.Context) -> None:
        await self.do_test_command(ctx, "reddit get", "python")

    async def test_redditcog_settings(self, ctx: commands.Context) -> None:
        await self.do_test_command(ctx, "reddit settings")

    async def test_redditcog_sort(self, ctx: commands.Context) -> None:
        await self.do_test_command(ctx, "reddit sort")

    async def test_redditcog_time(self, ctx: commands.Context) -> None:
        await self.do_test_command(ctx, "reddit time")

    async def test_redditcog_subs(self, ctx: commands.Context) -> None:
        await self.do_test_command(ctx, "reddit subs")

    # SoundCog
    @voice
    async def test_soundcog_connect(self, ctx: commands.Context) -> None:
        await self.do_test_command(ctx, "connect")

    @voice
    async def test_soundcog_play(self, ctx: commands.Context) -> None:
        await self.do_test_command(ctx, "play", "dota")

    @voice
    async def test_soundcog_queue(self, ctx: commands.Context) -> None:
        pass

    @voice
    async def test_soundcog_stop(self, ctx: commands.Context) -> None:
        await self.do_test_command(ctx, "stop")

    async def test_soundcog_destroy(self, ctx: commands.Context) -> None:
        await self.do_test_command(ctx, "destroy")

    async def test_soundcog_played(self, ctx: commands.Context) -> None:
        await self.do_test_command(ctx, "played")

    async def test_soundcog_search(self, ctx: commands.Context) -> None:
        await self.do_test_command(ctx, "search", "steven dawson")

    # StatsCog
    async def test_statscog_uptime(self, ctx: commands.Context) -> None:
        await self.do_test_command(ctx, "uptime")
        await self.do_test_command(ctx, "uptime", rtn=True, assertion=str, assert_type=True)

    async def test_statscog_changelog(self, ctx: commands.Context) -> None:
        await self.do_test_command(ctx, "changelog", rtn_type=list, assertion=list, assert_type=True)

    # TwitterCog
    @network_io
    async def test_twittercog_add(self, ctx: commands.Context) -> None:
        twitter_cog = self.bot.get_cog("TwitterCog")
        username = "vjemmie_test"
        if username in twitter_cog.users:
            await self.do_test_command(ctx, "twitter add", username, raises=CommandError)
        else:
            await self.do_test_command(ctx, "twitter add", username)

    async def test_twittercog_users(self, ctx: commands.Context) -> None:
        await self.do_test_command(ctx, "twitter users")

    # UserCog
    async def test_usercog_help(self, ctx: commands.Context) -> None:
        await self.do_test_command(ctx, "help")

    async def test_usercog_help_subcommands(self, ctx: commands.Context) -> None:
        await self.do_test_command(ctx, "help", "twitter")

    async def test_usercog_commands(self, ctx: commands.Context) -> None:
        await self.do_test_command(ctx, "commands")

    async def test_usercog_about(self, ctx: commands.Context) -> None:
        await self.do_test_command(ctx, "about")

    async def test_usercog_invite(self, ctx: commands.Context) -> None:
        await self.do_test_command(ctx, "invite")

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
