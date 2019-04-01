import asyncio
import secrets
import sys
from secrets import PFMSecrets

import discord
from discord.ext import commands
from discord.ext.commands import Bot

from cogs import *
from ext.checks import load_blacklist

# Bot setup
bot = Bot(command_prefix="!", description="Meme bot", pm_help=False)

# Add cogs
for k, v in dict(locals()).items():
    if k.endswith("Cog"):
        bot.add_cog(v(bot=bot))

dev = False if len(sys.argv)==1 else True
token = secrets.BOT_TOKEN if not dev else secrets.DEV_BOT_TOKEN
print(f"Dev: {dev}")
bot.run(token)
