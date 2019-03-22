import asyncio

import secrets
from secrets import PFMSecrets

import discord
from discord import opus
from discord.ext import commands
from discord.ext.commands import Bot


from cogs import *
from utils.config import GENERAL_DB_PATH
from cogs.db_cog import DatabaseHandler
from cogs.admin_utils import load_blacklist, error_handler

# Bot setup
bot = Bot(command_prefix="!", description="Meme bot", pm_help=False)
log_channel_id = 340921036201525248
# Add cogs
for k, v in dict(locals()).items():
    if k.endswith("Cog"):
        bot.add_cog(v(bot=bot, log_channel_id=log_channel_id))

@bot.check_once
def check_commands(ctx):
    return ctx.message.author.id not in load_blacklist()

@bot.listen()
async def on_message(message):
    if PFMSecrets.offensive_word(message) and message.author.id != bot.user.id:
        db = DatabaseHandler(GENERAL_DB_PATH)
        db.log_gaming_moment(message)
        await message.add_reaction(':cmonpfm:427842995748995082')

@bot.listen()
async def on_voice_state_update(member, before, after):
    if member.id == 103890994440728576:
        if not before.channel:
            channel = bot.get_channel(340921036201525248)
            await channel.send(f"Welcome to the voice channel {member.name}! :)")          

bot.run(secrets.BOT_TOKEN)