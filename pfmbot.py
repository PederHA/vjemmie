import asyncio
import sys

import secrets
from secrets import PFMSecrets

import discord
from discord.ext import commands
from discord.ext.commands import Bot


from cogs import *
from utils.config import GENERAL_DB_PATH
from cogs.db_cog import DatabaseHandler
from ext.checks import load_blacklist


# Bot setup
bot = Bot(command_prefix="!", description="Meme bot", pm_help=False)

# Add cogs
for k, v in dict(locals()).items():
    if k.endswith("Cog"):
        bot.add_cog(v(bot=bot))

#@bot.check_once
#def check_commands(ctx):
#    return ctx.message.author.id not in load_blacklist()

@bot.listen()
async def on_message(message):
    if PFMSecrets.offensive_word(message) and message.author.id != bot.user.id:
        db = DatabaseHandler(GENERAL_DB_PATH)
        db.log_gaming_moment(message)
        await message.add_reaction(':cmonpfm:427842995748995082')      

dev = False if len(sys.argv)==1 else True
token = secrets.BOT_TOKEN if not dev else secrets.DEV_BOT_TOKEN
print(f"Dev: {dev}")
bot.run(token)