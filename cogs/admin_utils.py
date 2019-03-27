import json
import traceback

from discord.ext import commands

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
