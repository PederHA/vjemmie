from discord.ext import commands
import discord

import requests
import shutil
from cogs.fryer import ImageFryer
from utils.exceptions import WordExceededLimit, NonImgURL, InvalidURL
from requests.exceptions import ConnectionError, MissingSchema
import traceback
from cogs.base_cog import BaseCog

class FryingCog(BaseCog):
    """Cog for deep frying images
    """

    @commands.command(name="deepfry")
    async def deepfry(self, ctx: commands.Context, image_url: str="", emoji: str="", text: str="", caption: str="") -> None:
        
        if not await self.is_img_url(image_url):
            if image_url == "emojis":
                emojis = await ImageFryer.get_files_in_dir("emojis")
                return await self.send_text_message(ctx, emojis)
            elif image_url == "captions":
                captions = await ImageFryer.get_files_in_dir("captions")
                return await self.send_text_message(ctx, emojis)
            else:
                help_cmd = self.bot.get_command("help")
                return await ctx.invoke(help_cmd, "frying")

        if len(text) > 26:
            raise discord.DiscordException("Text string cannot exceed 26 characters")
        
        try:
            img = await self.download_from_url(image_url)
            fryer = ImageFryer(img)
            img = fryer.fry(emoji, text, caption)
        except Exception as e:
            exc = traceback.format_exc()
            await self.log_error(ctx, exc)
            return await ctx.send("An unknown error occured.") 
        else:
            await ctx.send(file=discord.File(img, filename="deepfried.jpeg"))

