import argparse
import io
import traceback
from functools import partial
from typing import Optional, Union, Tuple

import discord
import pytesseract
from discord.ext import commands
from PIL import Image, ImageEnhance, ImageStat, ImageOps
import numpy as np

from .base_cog import BaseCog
from ..deepfryer.fryer import ImageFryer
from ..utils.checks import owners_only, pfm_cmd
from ..utils.exceptions import (BotException, FileSizeError,
                              InvalidURLError, NonImgUrlError,
                              WordExceededLimit, CommandError)
from ..utils.http import post


class ImageCog(BaseCog):
    """Image manipulation commands."""

    EMOJI = ":camera:"
    REMOVEBG_MAXSIZE = 240_000
    
    @commands.command(name="deepfry")
    async def deepfry(self, ctx: commands.Context, *args, rtn=False) -> None:
        "Deepfries an image. `!deepfry help` for usage info."
        if (
            not ctx.message.attachments and not args or 
            args and args[0] in ["help", "hlep", "?", "info"]
            ):
            out_str = (
                "**Required:** `-url` <url> ***OR*** an attached image"
                "\n**Optional:** `-text` `-emoji` `-caption`"
                "\n\nType `!deepfry -list <emojis/captions>` to see available emojis/captions"
                )
            return await self.send_embed_message(ctx, f"!{ctx.invoked_with}", out_str)
        
        # Add command parameters
        parser = argparse.ArgumentParser()
        for arg in ["-url", "-text", "-emoji", "-caption", "-list"]:
            parser.add_argument(arg, default=None, type=str)

        # Parse only arguments defined above
        a = parser.parse_known_args(args=args)[0]    
        
        # Post list of emojis/captions if -list argument
        if a.list:
            try:
                out = await ImageFryer.get_files_in_dir(a.list)
            except FileNotFoundError:
                return await ctx.send(f"No such category `{a.list}`")
            else:
                return await self.send_embed_message(ctx, a.list.capitalize(), out)      
        
        # Check if message has an attachment if no -url argument
        if not a.url:
            if not ctx.message.attachments:
                raise CommandError(
                    "Message must have a `-url` argument or an image attachment!"
                    )
            else:
                # Use URL of attachment
                a.url = ctx.message.attachments[0].url
        
        return await self._deepfry(ctx, 
                            url=a.url, 
                            emoji=a.emoji, 
                            text=a.text, 
                            caption=a.caption, 
                            rtn=rtn)

    
    async def _deepfry(self,
                      ctx: commands.Context,
                      url: str=None,
                      emoji: str=None,
                      text: str=None,
                      caption: str=None,
                      *args,
                      rtn: bool=False
                      ) -> Optional[Image.Image]:
        """Deepfries an image.
        
        Parameters
        ----------
        ctx : `commands.Context`
            Discord context
        url : `str`, optional
            Image URL
        emoji : `str`, optional
            Name of emoji to add to random coordinates on image
        text : `str`, optional
            Text to add to top of image
        caption : `str`, optional
            Name of caption image to add to bottom of image
        rtn : `bool`, optional
            Return fried image instead of posting it to ctx.channel
        
        Raises
        ------
        `discord.DiscordException`
            Raised if ctx.message has no image URL or image attachment
        
        Returns
        -------
        `Optional[Image.Image]`
            Fried image returned if argument rtn==True
        """
        # Check if url or attachment is an image
        if not isinstance(url, io.BytesIO) and not await self.is_img_url(url):
            raise CommandError("URL or attachment must be an image file!")
        
        # Download image if url if not a file-like object
        if not isinstance(url, io.BytesIO):
            img = await self.download_from_url(ctx, url)
        else:
            img = url
            
        # Deepfry
        fryer = ImageFryer(img)
        to_run = partial(fryer.fry, emoji, text, caption)
        fried_img = await self.bot.loop.run_in_executor(None, to_run)

        # Return Image.Image object if nuking
        if rtn:
            return fried_img
        
        # Upload fried image and get embed
        embed = await self.get_embed_from_img_upload(ctx, fried_img, "deepfried.jpg")
        await ctx.send(embed=embed)

    @commands.command(name="nuke")
    async def nuke(self, ctx: commands.Context, *args, passes: int=3) -> None:
        """Deeper frying."""
        
        # Initial frying, returns an Image.Image object
        img = await ctx.invoke(self.deepfry, *args, rtn=True)
        
        async with ctx.typing():
            for i in range(passes):
                img = await self._deepfry(ctx, img, rtn=True)
            else:
                # Finally send image on last pass of deepfrying
                await self._deepfry(ctx, img)
    
    @commands.command(name="blackhole")
    async def blackhole(self, ctx: commands.Context, *args) -> None:
        """Even deeper frying."""
        await ctx.invoke(self.nuke, *args, passes=7)        

    @commands.command(name="quantum")
    @owners_only()
    async def quantum(self, ctx: commands.Context, *args) -> None:
        """Deepest frying."""
        await ctx.invoke(self.nuke, *args, passes=20)

    @commands.command(name="removebg")
    @commands.cooldown(rate=2, per=300, type=commands.BucketType.user)
    async def remove_bg(self, ctx: commands.Context, image_url: Optional[str]=None) -> None:
        """Removes background from an image."""
        if not image_url:
            if ctx.message.attachments:
                image_url = ctx.message.attachments[0].url
            else:
                self.reset_command_cooldown(ctx)
                raise CommandError("Message has no image URL or image attachment")

        # Download image from URL
        img = await self.download_from_url(ctx, image_url)

        # Resize image to sub 0.25 MP, so we only have to use 1 r.bg credit per API call
        resized_img = await self._resize_img(img)

        # Upload image to remove.bg and receive no-bg version of image
        img_nobg = await self._use_removebg_api(resized_img)
        
        if not img_nobg:
            raise CommandError("Could not remove background! Try again later.")

        embed = await self.get_embed_from_img_upload(ctx, img_nobg, "nobg.png")
        await ctx.send(embed=embed)
    
    async def _use_removebg_api(self, image) -> Optional[io.BytesIO]:
        response = await post(
            'https://api.remove.bg/v1.0/removebg',
            files={'image_file': image},
            data={'size': 'auto'},
            headers={'X-Api-Key': self.bot.secrets.REMOVEBG_KEY},
        )
        if response.status_code != 200:
            j = response.json()
            try:
                err = j["errors"][0]["title"]
            except KeyError:
                err = response.text
            raise ConnectionError(err)

        img_nobg = io.BytesIO(response.content)
        img_nobg.seek(0)
        return img_nobg
   
    async def _resize_img(self, _img: io.BytesIO) -> io.BytesIO:
        image = Image.open(_img)
        width, height = image.size

        # Get new image dimensions
        new_w, new_h = await self.scale_to_target(width, height, self.REMOVEBG_MAXSIZE)

        # Construct new bytes object from resized image
        imgbuffer = io.BytesIO()
        new_img = image.resize((new_w, new_h), resample=Image.BICUBIC)
        new_img = new_img.convert("RGB")
        new_img.save(imgbuffer, format="JPEG")
        imgbuffer.seek(0)
        return imgbuffer

    async def scale_to_target(self, width: int, height: int, target: int) -> Tuple[int, int]:
        """Gets image dimensions as close as possible to a target size"""
        STEP_SIZE = 0.01
        TRIES = 200000
        
        # Scale up if image is smaller
        if target > width * height:
            STEP_SIZE = -STEP_SIZE
        
        for i in np.arange(0, STEP_SIZE*TRIES, STEP_SIZE):
            new = (width // i) * (height // i)
            if new <= target:
                break
        else:
            raise BotException("Failed to resize image!") # This should NEVER happen

        return int(abs(width//i)), int(abs(height//i))
    
    def resize_image(self, image: Image.Image, width: int=0, height: int=0) -> Image.Image:
        if not width and not height:
            raise ValueError("Width or height must be specified!")
        
        img_w, img_h = image.size

        if height:
            m = height / img_h
            width = img_w * m
        elif width:
            m = width / img_w
            height = img_h * m
        
        height, width = round(abs(height)), round(abs(width))

        image = image.resize((width, height), resample=Image.BICUBIC)
        
        return image

    def read_image_text(self, image: Union[str, bytes, Image.Image]) -> str:
        if not isinstance(image, Image.Image):
            image = Image.open(image)
        
        # Improves pytesseract accuracy
        image = self.optimize_image(image)

        text = pytesseract.image_to_string(image, lang="eng")
        
        return text

    def optimize_image(self, image: Image.Image) -> Image.Image:
        image = image.convert("L")  # Convert to greyscale
  
        image = ImageEnhance.Contrast(image).enhance(2)  # Increase contrast

        # Invert image if we suspect white text on dark background
        if ImageStat.Stat(image).mean[0] < 128:
            image = ImageOps.invert(image)

        image = self.resize_image(image, width=2000)

        return image

    @commands.command(name="totext", usage="<url> or <msg attachment>")
    async def img_to_txt(self, ctx: commands.Context, url: str=None) -> None:
        """Grab text from image."""
        if not url and not ctx.message.attachments:
            raise CommandError("An image URL or an image message attachment is required!")
        
        # Use attachment if it exists, else URL
        if ctx.message.attachments:
            url = ctx.message.attachments[0].url

        # Download image
        if not await self.is_img_url(url):
            raise CommandError("Attachment or URL is not an image!")      
        img = await self.download_from_url(ctx, url)

        try:
            image_text = await self.bot.loop.run_in_executor(None, self.read_image_text, img)
        except pytesseract.pytesseract.TesseractNotFoundError:
            await self.warn_owner("Tesseract is not installed or is not added to PATH!")
            raise CommandError("This command has not been properly configured by the bot owner yet.")
        await self.send_text_message(image_text, ctx)
