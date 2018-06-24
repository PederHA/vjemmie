from discord.ext import commands
import discord
from ext_module import ExtModule
import requests
import shutil

class TestingCog:
    """Testing Bot Commands
    """
    def __init__(self, bot: commands.Bot, log_channel_id: int=None):
        self.bot = bot
        self.log_channel_id = log_channel_id
        self.send_log = None
    
    async def on_ready(self):
        self.send_log = ExtModule.get_send_log(self)

    @commands.command(name="spotify")
    async def spotify_test(self, ctx: commands.Context, *args):
        if ctx.message.author.activity.__class__ == discord.activity.Spotify:
            album_cover_url = ctx.message.author.activity.album_cover_url
            self.download_album_art(album_cover_url)
            await ctx.send("I am listening to: " 
                          f"{ctx.message.author.activity.artist} - "
                          f"{ctx.message.author.activity.title}", file=discord.File("temp/album_cover.jpeg"))

    def download_album_art(self, url):
        r = requests.get(url, stream=True)
        with open("temp/album_cover.jpeg", 'wb') as f:
            r.raw.decode_content = True
            shutil.copyfileobj(r.raw, f)   
