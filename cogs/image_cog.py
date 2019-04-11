import io
import traceback
from functools import partial

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
                      caption: str=None) -> None:
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
            emoji, text, caption = url, emoji, text
            url = ctx.message.attachments[0].url
        
        # Check if url or attachment is an image
        if not await self.is_img_url(url):
            return await ctx.send("URL or attachment must be an image file!")

        try:
            # Download image
            img = await self.download_from_url(ctx, url)
            # Deepfry
            fryer = ImageFryer(img)
            fried_img = fryer.fry(emoji, text, caption)
        except Exception as e:
            exc = traceback.format_exc()
            await self.log_error(ctx, exc)
            return await ctx.send("An unknown error occured.")
        else:
            # Upload fried image
            msg = await self.upload_bytes_obj_to_discord(fried_img, "deepfried.jpg")
            image_url = msg.attachments[0].url
            
            # Send message with uploaded image
            embed = await self.get_embed(ctx, image_url=image_url)
            await ctx.send(embed=embed)
    
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
        
        def use_removebg_api(image) -> str:
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

        to_run = partial(use_removebg_api, resized_img)
        img_nobg = await self.bot.loop.run_in_executor(None, to_run)
        
        if not img_nobg:
            return await ctx.send("Could not remove background! Try again later.")

        await ctx.send(file=discord.File(img_nobg, "nobg.png"))
    
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
