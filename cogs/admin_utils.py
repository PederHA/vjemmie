from discord.ext import commands
import json
import traceback

admins = [103890994440728576]

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
        return ctx.message.author.id in admins
    return commands.check(predicate)


# Check added via modifying attributes of discord commands (very hacky and bad tbqh)
def is_not_blacklisted(ctx):
    def predicate(ctx):
        blacklist = load_blacklist()
        return ctx.message.author.id not in blacklist
    return predicate(ctx)

# TODO: ADD BLACKLIST(ID, COMMAND)! ex: !blacklist Huya play
async def error_handler(bot, ctx, error, *bugged_params) -> None:
    if bugged_params: # Sometimes two instances of self is passed in, totaling 4 args instead of 3
        ctx = error
        error = bugged_params[0]
    error_msg = error.args[0]
    if "The check functions" in error_msg: # lack of user privileges
        await ctx.send("Insufficient rights to perform command!")
    else:
        await unknown_error(ctx)

async def unknown_error(bot, ctx):
    not_unknown = [
        "Command raised an exception", 
        "MissingRequiredArgument"     
    ]
    ignore = []
    error_msg = traceback.format_exc()
    last_exception_line = error_msg.splitlines()[-1]
    if any(x in last_exception_line for x in not_unknown) and not any(x in last_exception_line for x in ignore):
        *_, user_error = last_exception_line.split(":")
        out_msg = user_error
    else:
        out_msg = "An unknown error occured"
    await ctx.send(out_msg) # Display error to user
    await self.send_log(error_msg, ctx) # Send entire exception traceback to log channel