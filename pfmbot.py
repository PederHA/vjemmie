import secrets
from discord.ext.commands import Bot
from discord.ext import commands
import discord
import bs4 as bs
import asyncio
from cogs.sound_cog import SoundboardCog
from cogs.admin_cog import AdminCog
from cogs.user_cog import UserCog
from cogs.pubg_cog import PUBGCog
from cogs.youtube_cog import YTCog
from cogs.wowprogress_cog import WPCog
from cogs.pfm_memes_cog import PFMCog
from cogs.reddit_cog import RedditCog
from cogs.fun_cog import FunCog
from discord import opus
from ext_module import ExtModule
from events_module import EventsModule
from secrets import PFMCrypto

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
bot.add_cog(FunCog(bot=bot, log_channel_id=log_channel_id))

@bot.async_event
def on_ready():
    print("Client logged in")

# Move out of main?
@bot.listen()
async def on_message(message):
    if EventsModule.is_travis(message):
        #travis_message = message.content.lower()
        #if message.author.voice.channel.id == 133332608762380289:
            #await message.author.voice.channel.disconnect()
        pass
    if EventsModule.is_rad(message):
        if any(word in message.content.lower() for word in secrets.RAD_WORDS):
            await message.add_reaction(':PedoRad:237754662361628672')
    if PFMCrypto.base64_compare(message):
        await message.add_reaction(':cmonpfm:427842995748995082')
    
    #await bot.process_commands(message)

bot.run(secrets.BOT_TOKEN)