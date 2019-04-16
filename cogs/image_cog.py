import io
import traceback
from functools import partial
from typing import Optional
import argparse

import discord
import requests
from discord.ext import commands
from PIL import Image

from botsecrets import REMOVEBG_API_KEY
from cogs.base_cog import BaseCog
from deepfryer.fryer import ImageFryer
from ext.checks import owners_only, pfm_cmd
from utils.exceptions import InvalidURL, NonImgURL, WordExceededLimit


class ImageCog(BaseCog):
    """Image manipulation commands."""

    EMOJI = ":camera:"

    @commands.command(name="deepfry")
    async def deepfry(self, ctx: commands.Context, *args, rtn=False) -> None: 
        if (
            not ctx.message.attachments and not args or 
            args and args[0] in ["help", "hlep", "?", "info"]
            ):
            out_str = (
                "**Required:** `-url` <url> or an attached image"
                "\n**Optional:** `-text` `-emoji` `-caption`"
                "\n\nType `!deepfry -list <emoji/caption>` to see available emojis/captions"
                )
            return await self.send_embed_message(ctx, ctx.invoked_with, out_str)
        
        parser = argparse.ArgumentParser()
        
        # Add possible user arguments to parser
        parser.add_argument("-url", default=None, type=str) 
        parser.add_argument("-text", default=None, type=str)
        parser.add_argument("-emoji", default=None, type=str)
        parser.add_argument("-caption", default=None, type=str)
        parser.add_argument("-list", default=None, type=str)

        # Parse only arguments defined above
        a = parser.parse_known_args(args=args)[0]    
        
        # Post list of emojis/captions if -list argument
        if a.list:
            if a.list in ["emojis", "captions"]:
                out = await ImageFryer.get_files_in_dir(a.list)
                return await self.send_embed_message(ctx, a.list.capitalize(), out)
            else:
                return await ctx.send(f"No such category `{a.list}`") 
        
        # If no -url argument, check if message has an attachment
        if not a.url:
            if not ctx.message.attachments:
                raise AttributeError(
                    "Message must have a `-url` argument or an image attachment!"
                    )
            else:
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
        ValueError
            Raised if ctx.message has no image URL or image attachment
        
        Returns
        -------
        `Optional[Image.Image]`
            Fried image returned if argument rtn==True
        """
        # Check if url or attachment is an image
        if not isinstance(url, io.BytesIO) and not await self.is_img_url(url):
            raise ValueError("URL or attachment must be an image file!")

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
            if rtn:
                return fried_img
            
            # Upload fried image and get embed
            embed = await self.get_embed_from_img_upload(ctx, fried_img, "deepfried.jpg")
            await ctx.send(embed=embed)

    @commands.command(name="nuke")
    async def nuke(self, ctx: commands.Context, *args, passes: int=3) -> None:
        """Deeper frying. Same arguments as `!deepfry`"""
        
        # Initial frying, returns an Image.Image object
        img = await ctx.invoke(self.deepfry, *args, rtn=True)

        for i in range(passes):
            img = await self._deepfry(ctx, img, rtn=True)
        else:
            # Finally send image on last pass of deepfrying
            await self._deepfry(ctx, img)
    
    # I somehow couldn't get subcommands to work? This will do in the meantime
    @commands.command(name="blackhole")
    async def blackhole(self, ctx: commands.Context, *args) -> None:
        """Even deeper frying."""
        await ctx.invoke(self.nuke, *args, passes=7)        

    @commands.command(name="quantum")
    @owners_only()
    async def quantum(self, ctx: commands.Context, *args) -> None:
        """ADMIN ONLY: Deepest frying."""
        await ctx.invoke(self.nuke, *args, passes=20)

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

        # Upload image to remove.bg and receive no-bg version of image
        to_run = partial(self._use_removebg_api, resized_img)
        img_nobg = await self.bot.loop.run_in_executor(None, to_run)
        
        if not img_nobg:
            return await ctx.send("Could not remove background! Try again later.")

        embed = await self.get_embed_from_img_upload(ctx, img_nobg, "nobg.png")
        await ctx.send(embed=embed)
    
    def _use_removebg_api(self, image) -> Optional[io.BytesIO]:
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
