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
            embed = discord.Embed(title="Spotify", 
                                  description=f"{ctx.message.author.activity.artist} - {ctx.message.author.activity.title}", 
                                  type="link", 
                                  url=f"https://open.spotify.com/track/{ctx.message.author.activity.track_id}", provider=(None, "Spotify"), 
                                 )
            await ctx.send(f"**{ctx.message.author.name}** currently playing: " 
                          f"{ctx.message.author.activity.artist} - "
                          f"{ctx.message.author.activity.title}",
                          embed=embed, file=discord.File("temp/album_cover.jpeg"))
        else:
            await ctx.send("Unable to read Spotify information.")

    def download_album_art(self, url):
        r = requests.get(url, stream=True)
        with open("temp/album_cover.jpeg", 'wb') as f:
            r.raw.decode_content = True
            shutil.copyfileobj(r.raw, f)   

    @commands.command(name="get_msg")
    async def get_msg(self, ctx: commands.Context, *args):
        new_channel = self.bot.get_channel(340921036201525248)
        new_msg = await new_channel.get_message(460456222144069632)

        for m in new_msg.embeds:
            print(dir(m))
            print(repr(m.image))
            print(m.footer)
            print(m.url)
            m_dict = m.to_dict()
            for k, v in m_dict.items():
                print(k, v)
