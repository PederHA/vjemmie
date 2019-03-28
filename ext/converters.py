import re
from urllib.parse import urlparse

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