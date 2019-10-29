from ipaddress import ip_address, IPv4Address, IPv6Address
import re
from typing import Optional, Iterable, Union
from urllib.parse import urlparse, ParseResult
from functools import partial
from collections import defaultdict

import requests
import discord

from discord.ext import commands
from discord.ext.commands.converter import IDConverter, _get_from_guilds
from discord.ext.commands.errors import BadArgument

from utils.exceptions import CommandError
from utils.messaging import fetch_message
from config import YES_ARGS


class MemberOrURLConverter(IDConverter):
    """Converts to a :class:`Member` if possible.
    If object passed in is a string that looks like an HTTP/HTTPS
    URL, returns string.

    All lookups are via the local guild. If in a DM context, then the lookup
    is done by the global cache.

    The lookup strategy is as follows (in order):

    1. Lookup by ID.
    2. Lookup by mention.
    3. Lookup by name#discrim
    4. Lookup by name
    5. Lookup by nickname
    """

    async def convert(self, ctx, argument):
        bot = ctx.bot
        match = self._get_id_match(argument) or re.match(r'<@!?([0-9]+)>$', argument)
        guild = ctx.guild
        result = None
        if match is None:
            # not a mention...
            if guild:
                result = guild.get_member_named(argument)
            else:
                result = _get_from_guilds(bot, 'get_member_named', argument)
        else:
            user_id = int(match.group(1))
            if guild:
                result = guild.get_member(user_id)
            else:
                result = _get_from_guilds(bot, 'get_member', user_id)
        if urlparse(argument).scheme in ["http", "https"]:
            result = argument

        if result is None:
            raise BadArgument(f"{argument} is neither a Member nor a valid URL")

        return result

class UserOrMeConverter(IDConverter):
    """Converts to a :class:`User`.

    All lookups are via the global user cache.

    The lookup strategy is as follows (in order):

    1. Lookup by ID.
    2. Lookup by mention.
    3. Lookup by "me", "self" arguments
    3. Lookup by name#discrim
    4. Lookup by name
    """
    async def convert(self, ctx, argument):
        if argument is None:
            return ctx.bot.get_user(ctx.message.author.id)
        match = self._get_id_match(argument) or re.match(r'<@!?([0-9]+)>$', argument)
        result = None
        state = ctx._state
        
        if match is not None:
            user_id = int(match.group(1))
            result = ctx.bot.get_user(user_id)
        else:
            arg = argument
            # Check if argument contains one of the following phrases
            if arg in ["me", "-", ".", "self"]:
                # Return message author's user
                result = ctx.bot.get_user(ctx.message.author.id) 
            # check for discriminator if it exists
            if len(arg) > 5 and arg[-5] == '#':
                discrim = arg[-4:]
                name = arg[:-5]
                predicate = lambda u: u.name == name and u.discriminator == discrim
                result = discord.utils.find(predicate, state._users.values())
            if result is not None:
                return result

            predicate = lambda u: u.name == arg
            result = discord.utils.find(predicate, state._users.values())

        if result is None:
            raise BadArgument('User "{}" not found'.format(argument))

        return result


class ParsedURL(ParseResult):
    @property
    def original(self) -> str:
        return self.geturl()


class URLConverter(commands.Converter):
    SCHEMES = ["http", "https"]
    EXTENSIONS = []
    CATEGORY = ""

    @property
    def category(self) -> str:
        return self.__class__.__name__.split("Converter")[0]

    async def convert(self, 
                      ctx: commands.Context, 
                      arg: Optional[str]
                      ) -> Optional[ParseResult]:
        # Simply return arg if None is passed in
        if arg is None:
            return arg
        
        # Parse URL
        u = urlparse(arg)
        url = ParsedURL(u.scheme, u.netloc, u.path, u.params, u.query, u.fragment)

        if self.EXTENSIONS and not any(url.path.lower().endswith(ext)
                                       for ext in self.EXTENSIONS):
            if self.category:
                msg = f"URL file extension is not a valid {self.category} filetype."
            else:
                msg = "URL file extension is invalid"
            raise BadArgument(msg)

        if not url.scheme:
            raise BadArgument("URL is missing scheme.")

        if url.scheme not in self.SCHEMES:
            raise BadArgument("URL scheme must be HTTP or HTTPS")
        
        if "." not in url.netloc:
            raise BadArgument("URL lacks top-level domain!")
        
        return url


class SoundURLConverter(URLConverter):
    EXTENSIONS = [".mp3", ".m4a", ".wav"]


class ImgURLConverter(URLConverter):
    EXTENSIONS = [".jpeg", ".jpg", ".png", ".gif", ".webp"]


class SteamID64Converter(commands.Converter):
    attempts = defaultdict(int)

    async def convert(self, ctx: commands.Context, arg: str) -> Optional[str]:
        # Look up arg on steamid.io
        lookup = partial(requests.post, "https://steamid.io/lookup", data={"input": arg})
        r = await ctx.bot.loop.run_in_executor(None, lookup)
        
        if r.status_code != 200:
            raise ConnectionError("SteamID lookup returned non-200 code")
        
        try:
            steamid = r.text.split("data-steamid64=")[1].split('"', 2)[1]
            if not steamid.isnumeric():
                raise ValueError
        except (IndexError, ValueError):
            raise CommandError(f"Unable to find user {arg}")
        else:
            return steamid
        finally:
            id_ = ctx.message.author.id
            # Allow user 3 attempts to fetch their SteamID before starting cooldown
            self.attempts[id_] += 1
            if self.attempts[id_] <= 3:
                ctx.command.reset_cooldown(ctx)
            else:
                # Clear attempts counter, but start cooldown
                self.attempts[id_] = 0 


class BoolConverter(commands.Converter):
    """User-extensible bool converter.
    
    Users can supply a list of arguments in the object's constructor that
    represent truth-like values.
    """ 
    def __init__(self, options: Iterable) -> None:
        super().__init__()
        self.options = list(options)

    async def convert(self, ctx: commands.Context, arg: Union[bool, str]) -> bool: 
        if isinstance(arg, bool):
            return arg

        if isinstance(arg, str):
            arg = arg.lower()
            return arg in self.options + YES_ARGS

        return False


class MessageIdOrStringConverter(commands.Converter):
    """Accepts a message ID or a string. Returns `str`."""
    async def convert(self, ctx: commands.Context, arg: str) -> str:
        if arg.isnumeric():
            msg = fetch_message(ctx, arg)
            return msg.content
        else:
            return arg


class IPAddressConverter(commands.Converter):
    """Accepts a message ID or a string. Returns `str`."""
    async def convert(self, ctx: commands.Context, arg: str) -> Union[IPv4Address, IPv6Address]:
        try:
            return ip_address(arg)
        except ValueError:
            raise CommandError(f"'{arg}' is not a valid IP Address!")