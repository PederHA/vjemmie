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

@bot.event
async def on_ready():
    print("Client logged in")


"""
async def testfunc():
        print ("Hello")
        sound = SoundboardCog(commands.Bot,folder='sounds')
        sound._load_songs('sounds')
        #await sound.play(340921036201525249,"mw2intervention")
        await asyncio.sleep(3)
        print ("World") 

loop = asyncio.get_event_loop()
loop.run_until_complete(testfunc())"""

#Sickass rad message reaction function that breaks the bot
"""@bot.event
async def on_message(message):
    if message.author.id == 133875264995328000:
        await message.add_reaction(':PedoRad:237754662361628672')
"""

bot.run(secrets.BOT_TOKEN)
"""
class Input(asyncio.Protocol):

    def __init__(self):
        super().__init__()
        self._transport = None

    def connection_made(self, transport):
        self._transport = transport

    def data_received(self, data):
        self._transport.write(data)


loop2 = asyncio.get_event_loop()
coro2 = serial_asyncio.create_serial_connection(loop2, Input, 'COM6', baudrate=9600)
loop2.run_until_complete(coro2)
loop2.run_forever()
loop2.close() """
