"""Very simple testing suite for the bot commands and methods that came 
about due to a severe lack of patience for reading testing framework 
documentation and failing to integrate existing testing frameworks 
with Discord commands.

It's pretty fucking bad, let's be real, but it gets the job done.
"""

import asyncio
import copy
import inspect
import traceback
import operator
import time
from itertools import cycle
from contextlib import contextmanager
from unittest.mock import Mock
from functools import wraps, partial
from pathlib import Path
from typing import Coroutine, Awaitable, ContextManager, Any, TypeVar, Callable, Optional

import discord
from discord.ext import commands

from ..cogs.base_cog import BaseCog
from ..utils.checks import owners_only, test_server_cmd
from ..utils.exceptions import CommandError
from ..utils.messaging import ask_user_yes_no

SENTINEL = object() # Shouldn't strictly be called "sentinel", but it's not a None-value either...
DEFAULT_OPERATOR = operator.eq

# Used for ImageCog tests
IMAGE_URL = "https://cdn.discordapp.com/attachments/560503336013529091/630814900897185813/D846i0ZWwAcH-k_.png"

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
    def outer(f: Callable) -> Callable:
        setattr(f, attr_k, attr_v)
        @wraps(f)
        async def wrapper(*args, **kwargs) -> Optional[Any]:
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

    DIRS = ["tests/logs"]

    def __init__(self, bot: commands.Bot) -> None:
        super().__init__(bot)
        self.pfix = self.bot.command_prefix
        
        self.verbose = True
        self.msg_enabled = False
        self.network_io_enabled = False # Enables commands such as: !meme, !reddit get, !twitter add
        self.discord_io_enabled = False # Enables commands such as: !fuckup, !mlady

        self.test_id: Optional[int] = None # id of a set of active tests

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
            if await ask_user_yes_no(ctx, msg):
                await ctx.send(
                    "Proceeding with incomplete testing!\n"
                    "**NOTE:** In order to run all tests you must be connected to a voice channel!")
            else:
                return await ctx.send("Aborting.")
  
        # Store test results
        passed = []
        failed = []

        # Run pre-test configuration
        await self._pre_tests_setup()

        # Temporarily patch ctx to disable message sending while invoking bot commands
        with self.patch_ctx(ctx) as ctx_: 
            for test in [k for k in dir(self) if k.startswith("test_")]:
                # Get coroutine
                coro = getattr(self, test)

                # If test cannot be run, skip it
                if not self.determine_run_coro(coro, ctx_):
                    continue 
                
                # Test coroutine
                try:
                    await coro(ctx_)
                except:
                    failed.append(test)
                else:
                    passed.append(test)
       
        await self._post_tests_cleanup(ctx)
       
        # Format results
        passed_fmt = "\n".join(passed)
        failed_fmt = "\n".join(failed)

        print("Tests completed!")
        print(f"{len(passed)}/{len(passed) + len(failed)} tests passed!")
        if failed:
            print(f"Failed:\n{failed_fmt}")

        if not failed:
            result = "All tests passed!"
        elif not passed:
            result = "All tests failed"
        else:
            result = f"Passed:\n{passed_fmt}\n\nFailed:\n{failed_fmt}\n"
        
        await self.send_text_message(result, ctx)

    def determine_run_coro(self, coro, ctx: commands.Context) -> bool:
        """Checks if certain conditions are met, in order to determine
        if coroutine should be tested."""
        if not self.network_io_enabled and hasattr(coro, "network_io"):
            return False
        elif not self.discord_io_enabled and hasattr(coro, "discord_io"):
            return False
        elif not ctx.message.author.voice and hasattr(coro, "voice"):
            return False
        elif not inspect.iscoroutinefunction(coro):
            return False
        else:
            return True

    async def _pre_tests_setup(self) -> None:
        # Generate unique ID for tests
        self.test_id = int(time.time())
    
    async def _post_tests_cleanup(self, ctx) -> None:
        """Calls methods required for cleanup after running tests."""
        # Destroy audio player
        sc = self.bot.get_cog("SoundCog")
        await ctx.invoke(sc.destroy_player)

        # Reset test ID
        self.test_id = None

    @contextmanager
    def patch_ctx(self, ctx: commands.Context) -> ContextManager[commands.Context]:
        """Patches the `send()` method of a 
        `discord.ext.commands.Context` object with a dummy method
        that disables message sending while tests are running."""
        async def new_send(*args, **kwargs):
            pass
        setattr(new_send, "testing", True) # NOTE: Useless? What was the plan here?
        #new_send.testing = True 

        new_ctx = copy.copy(ctx) 
        if not self.msg_enabled:
            # Patch ctx.send with dummy method
            new_ctx.send = new_send
        yield new_ctx

    async def _do_test(self, coro_or_cmd, *args, **kwargs) -> None:
        """This is a dumpster fire."""
        # Pop ctx
        ctx = kwargs.pop("ctx", None)
        
        # Get name of command or coro, str formatted args and str formatted kwargs
        cmd_name, _args, _kwargs = await self._get_test_attrs(coro_or_cmd, *args, **kwargs)
        
        # Show args & kwargs if verbose is enabled
        a_kw = f"{_args} {_kwargs}" if self.verbose else ""
        
        # Object to test equality of result with
        assertion = kwargs.pop("assertion", SENTINEL)

        # same as TestCase.assertRaises
        raises = kwargs.pop("raises", None)

        in_ = kwargs.pop("in_", None)

        index = kwargs.pop("index", SENTINEL)

        # Get operator for assertion statement (default: ==)
        op = await self._get_operator(kwargs) # TODO: UNFINISHED!!

        passed = False
        try:
            # Await coro or command
            if ctx:
                r = await ctx.invoke(coro_or_cmd, *args, **kwargs)
            else:
                if inspect.iscoroutinefunction(coro_or_cmd):
                    r = await coro_or_cmd(*args, **kwargs)
                else:
                    r = coro_or_cmd(*args, **kwargs)
            
            # Assert returned value == assertion, if specified
            if assertion is not SENTINEL:
                if isinstance(assertion, type):
                    assert op(type(r), assertion)
                else:
                    if index is not SENTINEL:
                        r = r[0]
                    if in_:
                        r = getattr(r, in_)
                        op = operator.contains
                    assert op(r, assertion)

        except AssertionError:
            await self._format_assertion_error(r, cmd_name, assertion)
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
    
    async def _get_operator(self, kwargs: dict) -> Callable:
        op = kwargs.pop("op", None)
        if inspect.isbuiltin(op):
            return op
        else:
            return DEFAULT_OPERATOR

    async def _format_assertion_error(self, result: Any, cmd_name: str, assertion: Any) -> None:
        await self.log_test_error(cmd_name)
        if assertion is not SENTINEL:
            r = type(result) if isinstance(assertion, type) else result
            print(f"Expected {assertion}, got {r}")

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
        """Logs test error to log file and optionally prints 
        traceback of error."""
        exc_info = traceback.format_exc()
        
        p = Path(f"tests/logs/{self.test_id}.txt")
        
        if not p.exists():
            p.touch()
        
        with open(p, "a") as f:
            f.write(exc_info)
            f.write("\n\n")

        if self.verbose:
            print(exc_info)

    async def _get_test_attrs(self, coro_or_cmd, *args, **kwargs) -> tuple:
        # Get coroutine or command's name
        try:
            coro_or_cmd_name = coro_or_cmd.__func__.__name__
        except:
            coro_or_cmd_name = f"{self.pfix}{coro_or_cmd.qualified_name}"

        # String formatted args, kwargs
        _args = f"{' '.join([repr(arg) for arg in args])}" if args else ""
        _kwargs = f"{', '.join([f'{k}={v}' for k, v in kwargs.items()])}" if kwargs else ""

        return coro_or_cmd_name, _args, _kwargs

    async def do_test_coro(self, coro, *args, **kwargs) -> None:
        return await self._do_test(coro, *args, **kwargs)

    async def do_test_command(self, ctx: commands.Context, cmd: commands.Command, *args, **kwargs) -> None:
        if isinstance(cmd, str):
            cmd = self.bot.get_command(cmd)
            
        ctx.command = cmd
        
        if not cmd:
            raise TypeError("Command must be name of command or discord.ext.commands.Command object!")
        
        return await self._do_test(cmd, *args, **kwargs, ctx=ctx)

    async def do_test_cog_method(self, cog_name: str, meth_name: str, *args, **kwargs) -> None:
        """Tests a non-command method in a Cog."""
        cog = self.bot.get_cog(cog_name)
        method = getattr(cog, meth_name, None)
        await self._do_test(method, *args, **kwargs)
        

    #########################################
    #####             TESTS             #####
    #########################################

    # AdminCog
    @discord_io
    async def test_admincog_serverlist(self, ctx: commands.Context) -> None:
        await self.do_test_command(ctx, "serverlist")
    
    async def test_admincog_trusted_show(self, ctx: commands.Context) -> None:
        await self.do_test_command(ctx, "trusted show")

    async def test_admincog_trusted_add(self, ctx: commands.Context) -> None:
        await self.do_test_command(ctx, "trusted add", self.bot.user)

    async def test_admincog_trusted_remove(self, ctx: commands.Context) -> None:
        await self.do_test_command(ctx, "trusted remove", self.bot.user)

    # AutoChessCog
    async def test_autochesscog_stats_self(self, ctx: commands.Context) -> None:
        await self.do_test_command(ctx, "autochess stats")
    
    async def test_autochesscog_stats_specific(self, ctx: commands.Context) -> None:
        """Must be a user that is added and the bot can find through its UserOrMeConverter"""
        await self.do_test_command(ctx, "autochess stats", "TRVLLFJVZ") # 
    
    async def test_autochesscog_stats_specific_notfound(self, ctx: commands.Context) -> None:
        """Must be a user that cannot be found through UserOrMeConverter"""
        await self.do_test_command(ctx, "autochess stats", "ASDQWERTYFOOBAR69", raises=commands.errors.BadArgument)
    
    async def test_autochesscog_stats_specific_notadded(self, ctx: commands.Context) -> None:
        """Must be a user that is NOT added but can be found through UserOrMeConverter"""
        await self.do_test_command(ctx, "autochess stats", "PFM_SoundboardProxy", raises=CommandError)    

    # AvatarCog
    @discord_io
    async def test_avatarcog_fuckup(self, ctx: commands.Context) -> None:
        """AvatarCog command where `template_overlay == False`"""
        await self.do_test_command(ctx, "fuckup")

    @discord_io
    async def test_avatarcog_mlady(self, ctx: commands.Context) -> None:
        """AvatarCog command where `template_overlay == True`"""
        await self.do_test_command(ctx, "mlady")

    # FunCog
    async def test_funcog_roll_1_100(self, ctx: commands.Context) -> None:
        await self.do_test_command(ctx, "roll", 1, 100)
    
    async def test_funcog_roll_foo_bar_fails(self, ctx: commands.Context) -> None:
        await self.do_test_command(ctx, "roll", "foo", "bar", raises=CommandError)

    async def test_funcog_random(self, ctx: commands.Context) -> None:
        await self.do_test_command(ctx, "random", "Jeff", "Steve", "Travis", "Hugo")

    async def test_funcog_braille(self, ctx: commands.Context) -> None:
        await self.do_test_command(ctx, "braille", "testing braille command")
    
    async def test_funcog_big_text(self, ctx: commands.Context) -> None:
        chars = "".join([chr(i) for i in range(192, 256)])
        await self.do_test_cog_method("FunCog", "big_text", text=chars)

    # PUBGCog
    async def test_pubgcog_drop(self, ctx: commands.Context) -> None:
        await self.do_test_command(ctx, "drop", "erangel", "hot")

    async def test_pubgcog_crate(self, ctx: commands.Context) -> None:
        await self.do_test_command(ctx, "crate")
    
    @voice
    async def test_pubgcog_crate_c_fails(self, ctx: commands.Context) -> None:
        await self.do_test_command(ctx, "crate", "c", raises=CommandError)

    # RedditCog
    @network_io
    async def test_redditcog_meme(self, ctx: commands.Context) -> None:
        await self.do_test_command(ctx, "meme")

    @network_io
    async def test_redditcog_meme_fried(self, ctx: commands.Context) -> None:
        await self.do_test_command(ctx, "meme", "fried")

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
    async def test_soundcog_play_specific(self, ctx: commands.Context) -> None:
        await self.do_test_command(ctx, "play", "dota")
    
    @voice
    async def test_soundcog_play_random(self, ctx: commands.Context) -> None:
        await self.do_test_command(ctx, "play") # Tests random sound selection

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
    
    #async def test_soundcog_search_type(self, ctx: commands.Context) -> None:
    #    await self.do_test_command(ctx, "search", "steven dawson", rtn=True, assertion=list)
    #
    #async def test_soundcog_search_result(self, ctx: commands.Context) -> None:
    #    await self.do_test_command(ctx, "search", "steven dawson", rtn=True, assertion="steven dawson", index=0, in_="description")
    
    @voice
    @network_io
    async def test_soundcog_tts_default(self, ctx: commands.Context) -> None:
        await self.do_test_command(ctx, "tts", "test")
    
    @voice
    @network_io
    async def test_soundcog_tts_language(self, ctx: commands.Context) -> None:
        await asyncio.sleep(0.5)
        await self.do_test_command(ctx, "tts", "test", "sv")
    
    @voice
    @network_io
    async def test_soundcog_tts_filename(self, ctx: commands.Context) -> None:
        await asyncio.sleep(0.5)
        await self.do_test_command(ctx, "tts", "test", "en", "customfilename")    
    
    # StatsCog
    async def test_statscog_uptime(self, ctx: commands.Context) -> None:
        await self.do_test_command(ctx, "uptime")

    async def test_statscog_changelog_type(self, ctx: commands.Context) -> None:
        await self.do_test_command(ctx, "changelog")
    
    async def test_statscog_ping(self, ctx: commands.Context) -> None:
        await self.do_test_command(ctx, "ping")
    
    async def test_statscog_get_bot_uptime_str(self, ctx: commands.Context) -> None:
        await self.do_test_cog_method("StatsCog", "get_bot_uptime", type=str)    

    async def test_statscog_get_bot_uptime_dict(self, ctx: commands.Context) -> None:
        await self.do_test_cog_method("StatsCog", "get_bot_uptime", type=dict) 

    async def test_statscog_get_top_commands_for_guild(self, ctx: commands.Context) -> None:
        await self.do_test_cog_method("StatsCog", "get_top_commands_for_guild", guild_id=ctx.guild.id)

    async def test_statscog_get_top_commands_for_user(self, ctx: commands.Context) -> None:
        await self.do_test_cog_method("StatsCog", "get_top_commands_for_user", guild_id=ctx.guild.id, user=ctx.message.author)

    async def test_statscog_get_top_command_users(self, ctx: commands.Context) -> None:
        await self.do_test_cog_method("StatsCog", "get_top_command_users", guild_id=ctx.guild.id, command="run_tests")
    
    async def test_statscog_get_command_usage(self, ctx: commands.Context) -> None:
        await self.do_test_cog_method("StatsCog", "get_command_usage", guild_id=ctx.guild.id, command="run_tests", assertion=int)    
    
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

    async def test_usercog_help_category_sound(self, ctx: commands.Context) -> None:
        await self.do_test_command(ctx, "help", "sound")

    async def test_usercog_help_command_play(self, ctx: commands.Context) -> None:
        await self.do_test_command(ctx, "help", "play")
    
    async def test_usercog_help_command_deepfry(self, ctx: commands.Context) -> None:
        await self.do_test_command(ctx, "help", "deepfry")

    async def test_usercog_commands(self, ctx: commands.Context) -> None:
        await self.do_test_command(ctx, "commands")

    async def test_usercog_about(self, ctx: commands.Context) -> None:
        await self.do_test_command(ctx, "about")

    async def test_usercog_invite(self, ctx: commands.Context) -> None:
        await self.do_test_command(ctx, "invite")

    # ImageCog
    @discord_io
    async def test_imagecog_totext(self, ctx: commands.Context) -> None:
        await self.do_test_command(ctx, "totext", IMAGE_URL)

    @discord_io
    async def test_imagecog_deepfry(self, ctx: commands.Context) -> None:
        await self.do_test_command(ctx, "deepfry", "-url", IMAGE_URL)


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
