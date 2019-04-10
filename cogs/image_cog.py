from discord.ext import commands
import discord

import requests
import shutil
from cogs.fryer import ImageFryer
from utils.exceptions import WordExceededLimit, NonImgURL, InvalidURL
import traceback
from cogs.base_cog import BaseCog

class ImageCog(BaseCog):
    """Image manipulation commands."""

    @commands.command(name="deepfry")
    async def deepfry(self,
                      ctx: commands.Context,
                      url: str=None,
                      emoji: str=None,
                      text: str=None,
                      caption: str=None) -> None:
        """Deepfries an image"""
        # Check if user requests help
        if url in ["help", "h", "?"]:
            if emoji == "emojis":
                emojis = await ImageFryer.get_files_in_dir("emojis")
                return await self.send_text_message(ctx, emojis)
            elif emoji == "captions":
                captions = await ImageFryer.get_files_in_dir("captions")
                return await self.send_text_message(ctx, emojis)
            else:
                help_cmd = self.bot.get_command("help")
                return await ctx.invoke(help_cmd, "frying")
        
        # Check if url or attachment is an image
        if not await self.is_img_url(url):
            return await ctx.send("URL or attachment must be an image file!")

        # Use attachment URL as image URL if message has attachment
        if ctx.message.attachments:
            emoji, text, caption = url, emoji, text
            url = ctx.message.attachments[0]

        # I think we can remove this one
        if len(text) > 26:
            return await ctx.send("Text string cannot exceed 26 characters")

        try:
            img = await self.download_from_url(ctx, url)
            fryer = ImageFryer(img)
            img = fryer.fry(emoji, text, caption)
        except Exception as e:
            exc = traceback.format_exc()
            await self.log_error(ctx, exc)
            return await ctx.send("An unknown error occured.")
        else:
            await ctx.send(file=discord.File(img, filename="deepfried.jpeg"))
