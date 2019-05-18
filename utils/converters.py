import re
from typing import Optional
from urllib.parse import urlparse, ParseResult

from discord.ext import commands
from discord.ext.commands.converter import IDConverter, _get_from_guilds
from discord.ext.commands.errors import BadArgument


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

