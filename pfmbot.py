from urllib.parse import urlencode
import secrets
import urllib.request
from discord.ext.commands import Bot
from discord.ext import commands
import discord
import bs4 as bs
import random
import time
import praw
import asyncio
import re
from cogs.sound_cog import SoundboardCog
from cogs.admin_cog import AdminCog
from cogs.user_cog import UserCog
from cogs.pubg_cog import PUBGCog
from cogs.youtube_cog import YTCog
from cogs.wowprogress_cog import WPCog
from cogs.pfm_memes_cog import PFMCog
from cogs.reddit_cog import RedditCog
from cogs.fun_cog import FunCog
#from cogs.react_cog import ReactCog
from discord import opus
from ext_module import ExtModule
import serial_asyncio

bot = Bot(command_prefix="!", description="Meme bot", pm_help=False)
sound_folder = 'sounds'
log_channel_id = int('340921036201525248')

bot.add_cog(SoundboardCog(bot=bot, folder=sound_folder, log_channel_id=log_channel_id))
bot.add_cog(AdminCog(bot=bot, log_channel_id=log_channel_id))
bot.add_cog(UserCog(bot=bot, log_channel_id=log_channel_id))
bot.add_cog(PUBGCog(bot=bot, log_channel_id=log_channel_id))
bot.add_cog(YTCog(bot=bot, log_channel_id=log_channel_id))
bot.add_cog(WPCog(bot=bot, log_channel_id=log_channel_id))
bot.add_cog(PFMCog(bot=bot, log_channel_id=log_channel_id))
bot.add_cog(RedditCog(bot=bot, log_channel_id=log_channel_id))
#bot.add_cog(ReactCog(bot=bot, log_channel_id=log_channel_id))
bot.add_cog(FunCog(bot=bot, log_channel_id=log_channel_id))

@bot.event
async def on_ready():
    print("Client logged in")

bot.run(secrets.BOT_TOKEN)
