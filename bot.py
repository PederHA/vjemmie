import sys
from contextlib import suppress

with suppress(ImportError):
    import uvloop
    uvloop.install()

from discord.ext.commands import Bot, Command

from cogs import COGS
from botsecrets import BOT_TOKEN
from utils.patching.commands import patch_command_signature

patch_command_signature(Command)

def main(token, cogs) -> None:       
    # Bot setup
    bot = Bot(command_prefix="!", description="Meme bot", pm_help=False)

    # Add cogs
    for cog in cogs:
        bot.add_cog(cog(bot=bot))

    # Run bot
    bot.run(token)

if __name__ == "__main__":
    main(BOT_TOKEN, COGS)