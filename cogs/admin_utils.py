from discord.ext import commands

admins = [103890994440728576]

def is_admin():
    def predicate(ctx):
        return ctx.message.author.id in admins
    return commands.check(predicate)