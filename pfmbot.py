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

bot = Bot(command_prefix="!", description="Meme bot", pm_help=False)
log_channel_id = 340921036201525248

bot.add_cog(SoundboardCog(bot=bot, log_channel_id=log_channel_id))
bot.add_cog(AdminCog(bot=bot, log_channel_id=log_channel_id))
bot.add_cog(UserCog(bot=bot, log_channel_id=log_channel_id))
bot.add_cog(PUBGCog(bot=bot, log_channel_id=log_channel_id))
bot.add_cog(YTCog(bot=bot, log_channel_id=log_channel_id))
bot.add_cog(WPCog(bot=bot, log_channel_id=log_channel_id))
bot.add_cog(PFMCog(bot=bot, log_channel_id=log_channel_id))
bot.add_cog(RedditCog(bot=bot, log_channel_id=log_channel_id))
bot.add_cog(FunCog(bot=bot, log_channel_id=log_channel_id))
#bot.add_cog(SerialSoundboardCog(bot=bot, folder=sound_folder, log_channel_id=log_channel_id))
bot.add_cog(TestingCog(bot=bot, log_channel_id=log_channel_id))
bot.add_cog(FryingCog(bot=bot, log_channel_id=log_channel_id))
bot.add_cog(WeatherCog(bot=bot, log_channel_id=log_channel_id))
bot.add_cog(CodCog(bot=bot, log_channel_id=log_channel_id))
bot.add_cog(War3Cog(bot=bot, log_channel_id=log_channel_id, replays_folder=None))
#bot.add_cog(Music(bot))

@bot.event
async def on_ready():
    print("Client logged in")

@bot.listen()
async def on_message(message):
    if PFMSecrets.offensive_word(message):
        db = DatabaseHandler(GENERAL_DB_PATH)
        db.whosaidit(message)
        await message.add_reaction(':cmonpfm:427842995748995082')

bot.run(secrets.BOT_TOKEN)