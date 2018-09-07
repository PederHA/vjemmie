from discord.ext import commands
import discord
from ext_module import ExtModule
import requests
import shutil
from cogs.fryer import ImageFryer

class FryingCog:
    """Cog for deep frying images
    """
    def __init__(self, bot: commands.Bot, log_channel_id: int=None):
        self.bot = bot
        self.log_channel_id = log_channel_id
        self.send_log = None
    
    async def on_ready(self):
        self.send_log = ExtModule.get_send_log(self)

    @commands.command(name="deepfry")
    async def deepfry(self, ctx: commands.Context, image_url="", emoji="", text="", caption="") -> None:
        args = (image_url, emoji, text, caption)
        if image_url != "list":
            try:
                fryer = ImageFryer(image_url)
                fryer.fry(emoji, text, caption)
            except:
                await ctx.send("Something went wrong when trying to fry the source provided. Make sure the URL is a direct link to an image.")
            else:
                await ctx.send(file=discord.File("deepfryer/temp/fried_img.jpg"))
        elif args[0] == "list":
            returned = ImageFryer.get_files_in_dir(args[1])
            if returned is not None:
                await ctx.send(returned)
            else:
                await ctx.send("**List syntax:** `!deepfry list <emojis/captions/all>`")        
        else:
            await ctx.send("**Syntax:** `!deepfry <URL to image \***required**> <emoji -_optional_> <text _optional_> <caption graphic _optional_>`")