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
                                  url=f"https://open.spotify.com/track/{ctx.message.author.activity.track_id}", 
                                  provider=(None, "Spotify") 
                                 )
            await ctx.send(f"**{ctx.message.author.name}** is currently listening to: " 
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
        message = int(args[0])
        new_channel = self.bot.get_channel(340921036201525248)
        new_msg = await new_channel.get_message(message)
        for m in new_msg.embeds:
            #print(dir(m))
            pass

        #print(dir(new_msg))
        for embed in new_msg.embeds:
            print(dir(embed))
            print(dir(embed.footer))
            print(embed.footer.text)

    @commands.command(name="run_code")
    async def run_code(self, ctx: commands.Context, args):
        print(args)
        print(repr(args))
        eval(args)
    
    @commands.command(name="emojis")
    async def emojis(self, ctx:commands.Context, *args):
        if len(args)>1:
            input_string = args[0]
            input_string = input_string.upper()
            
            emoji = args[1]

            input_string = input_string.replace(" ", f" {emoji} ")
            output_string = f"{emoji} {input_string} {emoji}"

            await ctx.send(output_string)