from discord.ext import commands
import json
import traceback

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


def is_not_blacklisted(ctx):
    def predicate(ctx):
        return ctx.message.author.id not in load_blacklist()
    return commands.check(predicate)
