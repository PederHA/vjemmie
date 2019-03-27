import json
import traceback
import re
from urllib.parse import urlparse


from discord.ext import commands
from discord.ext.commands.converter import IDConverter, _get_from_guilds
from discord.ext.commands.errors import BadArgument

owners = [103890994440728576]

# Blacklist serialization functions
def load_blacklist() -> list:
    with open("db/blacklist.json", "r") as f:
        blacklist = json.load(f)
        return blacklist

def save_blacklist(blacklist: list) -> None:
    with open("db/blacklist.json", "w") as f:
        json.dump(blacklist, f)


# Decorator check
def is_admin():
    def predicate(ctx):
        if hasattr(ctx.author, "guild_permissions"): # Disables privileged commands in PMs
            return ctx.author.guild_permissions.administrator or ctx.author.id in owners
        return False
    return commands.check(predicate)


def is_owner():
    def predicate(ctx):
        return ctx.message.author.id in owners
    return commands.check(predicate)


def is_not_blacklisted():
    def predicate(ctx):
        return ctx.message.author.id not in load_blacklist()
    return commands.check(predicate)


def guild_predicate(ctx, guild_id):
    if hasattr(ctx.author, "guild"):
        return ctx.message.author.guild.id == guild_id
    return False


def is_pfm():
    def predicate(ctx):
        return guild_predicate(ctx, 133332608296681472)
    return commands.check(predicate)


def is_dgvgk():
    def predicate(ctx):
        return guild_predicate(ctx, 178865018031439872)
    return commands.check(predicate)


def is_test_server():
    def predicate(ctx):
        return guild_predicate(ctx, 340921036201525248)
    return commands.check(predicate)

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