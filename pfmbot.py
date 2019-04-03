import sys

from discord.ext.commands import Bot

from cogs import COGS
from botsecrets import BOT_TOKEN, DEV_BOT_TOKEN

# Bot setup
bot = Bot(command_prefix="!", description="Meme bot", pm_help=False)

# Add cogs
for cog in COGS:
        bot.add_cog(cog(bot=bot))

# Development mode is triggered if arbitrary commandline arg is present
token = BOT_TOKEN if len(sys.argv)==1 or not DEV_BOT_TOKEN else DEV_BOT_TOKEN
dev = False if token==BOT_TOKEN else True

# Run bot
print(f"Dev mode: {dev}")
bot.run(token)
