import io
import traceback
from functools import partial
from typing import Optional

import discord
import requests
from discord.ext import commands
from PIL import Image

from botsecrets import REMOVEBG_API_KEY
from cogs.base_cog import BaseCog
from deepfryer.fryer import ImageFryer
from ext.checks import owners_only
from utils.exceptions import InvalidURL, NonImgURL, WordExceededLimit


class ImageCog(BaseCog):
    """Image manipulation commands."""

    EMOJI = ":camera:"

    @commands.command(name="deepfry")
    async def deepfry(self,
                      ctx: commands.Context,
                      url: str=None,
                      emoji: str=None,
                      text: str=None,
                      caption: str=None,
                      nuke: bool=False
                      ) -> Optional[discord.Embed]:
        """Deepfries an image"""
        # Check if user requests help
        if url in ["help", "h", "?"]:
            if emoji == "emojis":
                emojis = await ImageFryer.get_files_in_dir("emojis")
                return await self.send_text_message(emojis, ctx)
            elif emoji == "captions":
                captions = await ImageFryer.get_files_in_dir("captions")
                return await self.send_text_message(emojis, ctx)
            else:
                help_cmd = self.bot.get_command("help")
                return await ctx.invoke(help_cmd, "frying")
        
        # Use attachment URL as image URL if message has attachment
        if ctx.message.attachments:
            if not nuke:
                # shift arguments 1 param right if image is supplied as attachment
                # Example: !deepfry b "ye boi" top10animebetrayals. 
                # Attachment replaces URL arg, and the 3 first arguments are treated as emoji, text & caption
                emoji, text, caption = url, emoji, text
            url = ctx.message.attachments[0].url 


        # Check if url or attachment is an image
        if not isinstance(url, io.BytesIO) and not await self.is_img_url(url):
            return await ctx.send("URL or attachment must be an image file!")

        try:
            # Download image if url if not a file-like object
            if not isinstance(url, io.BytesIO):
                img = await self.download_from_url(ctx, url)
            else:
                img = url
            # Deepfry
            fryer = ImageFryer(img)
            to_run = partial(fryer.fry, emoji, text, caption)
            fried_img = await self.bot.loop.run_in_executor(None, to_run)
        except Exception as e:
            exc = traceback.format_exc()
            await self.log_error(ctx, exc)
            return await ctx.send("An unknown error occured.")
        else:
            # Return Image.Image object if nuking
            if nuke:
                return fried_img
            
            # Upload fried image and get embed
            embed = await self.get_embed_from_img_upload(ctx, fried_img, "deepfried.jpg")
            await ctx.send(embed=embed)

    @commands.command(name="nuke")
    @owners_only()
    async def nuke_image(self, ctx: commands.Context, url: str=None) -> None:
        """Pretty bad image nuking command."""
        img = await ctx.invoke(self.deepfry, url, nuke=True)
        # Remove any message attachments after first round of frying
        ctx.message.attachments = []
        for i in range(3):
            img = await ctx.invoke(self.deepfry, img, nuke=True)
        else:
            # Finally send image on last round of deepfrying
            await ctx.invoke(self.deepfry, img)



    @commands.command(name="removebg")
    @owners_only()
    async def remove_bg(self, ctx: commands.Context, image_url: str=None) -> None:
        """Removes background from an image."""
        if not image_url and not ctx.message.attachments:
            raise discord.DiscordException("Message has no image URL or image attachment")
        
        if ctx.message.attachments:
            image_url = ctx.message.attachments[0].url

        # Download image from URL
        img = await self.download_from_url(ctx, image_url)

        # Resize image to sub 0.25 MP, so we only have to use 1 r.bg credit per API call
        resized_img = await self._resize_img(img)
        
        def use_removebg_api(image) -> Optional[io.BytesIO]:
            response = requests.post(
                'https://api.remove.bg/v1.0/removebg',
                files={'image_file': image},
                data={'size': 'auto'},
                headers={'X-Api-Key': REMOVEBG_API_KEY},
            )
            if response.status_code == requests.codes.ok:
                img_nobg = io.BytesIO(response.content)
                img_nobg.seek(0)
                return img_nobg

        # Upload image to remove.bg and receive no-bg version of image
        to_run = partial(use_removebg_api, resized_img)
        img_nobg = await self.bot.loop.run_in_executor(None, to_run)
        
        if not img_nobg:
            return await ctx.send("Could not remove background! Try again later.")

        embed = await self.get_embed_from_img_upload(ctx, img_nobg, "nobg.png")
        await ctx.send(embed=embed)

    
    async def _resize_img(self, _img: io.BytesIO) -> io.BytesIO:
        image = Image.open(_img)

        MAX_SIZE = 240_000 # 0.24 Megapixels

        width, height = image.size

        # Do not scale down image size if image is smaller than 0.24 Megapixels
        if width*height < MAX_SIZE:
            return _img
        
        try:
            new_w, new_h = await self.scale_down_img(width, height, MAX_SIZE)
        except:
            # Fall back on brute force resizing if algorithm fails
            for i in range(1, 16, 1):
                new_w, new_h = width//i, height//i
                new_size = new_w * new_h
                if new_size > MAX_SIZE:
                    continue
                else:
                    break
            else:
                raise Exception("Image is way, way, way too large")
        
        new_img = io.BytesIO()
        image = image.resize((new_w, new_h), resample=Image.BICUBIC)
        image = image.convert("RGB")
        image.save(new_img, format="JPEG")
        new_img.seek(0)
        return new_img

    async def scale_down_img(self, width, height, target) -> None:
        """Scales down an image as close as possible to a target size"""
        async def get_division_n(width, height, target) -> float:
            n = 1
            tries = 0
            while True:
                new = width//n * height//n
                if new > target:
                    n += 0.01
                    continue
                else:
                    return n
                tries +=1
                if tries > 2000:
                    # Completely arbitrary number, but lets us have an exit clause
                    raise Exception("Fatal exception")
       
        n = await get_division_n(width, height, target)
        return int(abs(width//n)), int(abs(height//n))
