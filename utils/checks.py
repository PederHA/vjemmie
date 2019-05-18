import json

from discord.ext import commands

from config import DOWNLOADS_ALLOWED, OWNER_ID



# Blacklist serialization functions
def load_blacklist() -> list:
    with open("db/blacklist.json", "r") as f:
        blacklist = json.load(f)
        return blacklist

def save_blacklist(blacklist: list) -> None:
    with open("db/blacklist.json", "w") as f:
        json.dump(blacklist, f)


# Decorator check
def admins_only():
    def predicate(ctx):
        if hasattr(ctx.author, "guild_permissions"): # Disables privileged commands in PMs
            return ctx.author.guild_permissions.administrator
        return False
    return commands.check(predicate)


def owners_only():
    """Check if command invoker is in list of owners defined in config.py"""
    def predicate(ctx):
        return ctx.message.author.id == OWNER_ID
    return commands.check(predicate)


def is_not_blacklisted():
    def predicate(ctx):
        return ctx.message.author.id not in load_blacklist()
    return commands.check(predicate)


def guild_predicate(ctx, guild_id):
    if hasattr(ctx.author, "guild"):
        return ctx.message.author.guild.id == guild_id
    return False


def pfm_cmd():
    """PFM guild decorator"""
    def predicate(ctx):
        return guild_predicate(ctx, 133332608296681472)
    return commands.check(predicate)


def dgvgk_cmd():
    """DGVGK guild decorator"""
    def predicate(ctx):
        return guild_predicate(ctx, 178865018031439872)
    return commands.check(predicate)


def test_server_cmd():
    """Test/dev guild decorator"""
    def predicate(ctx):
        return guild_predicate(ctx, 340921036201525248)
    return commands.check(predicate)

def download_cmd():
    """Decorator for download commands"""
    def predicate(ctx):
        return ctx.cog.DOWNLOADS_ALLOWED
    return commands.check(predicate)

def disabled_cmd():
    """Decorator to disable a command for _everyone_"""
    def predicate(ctx):
        return False
    return commands.check(predicate)