import asyncio
import random
import traceback
import io
from pprint import pprint
from functools import partial
import math

import discord
import aiohttp
from discord.ext import commands
from PIL import Image

from cogs.base_cog import BaseCog
from botsecrets import REMOVEBG_API_KEY
import requests


class FunCog(BaseCog): 
    @commands.command(name='roll',
                      aliases=['dice'],
                      description='Random roll. Provide number argument to specify range (1-100 default).')
    async def roll(self, ctx: commands.Context, lower: int=0, upper: int=100) -> None:
        """!roll <range>"""      
        await ctx.send(random.randint(lower, upper))
            
    @commands.command(name='random')
    async def roll2(self, ctx: commands.Context, *args) -> None:
        """
        Select from  <thing1, thing2, ..., thinglast>
        """
        if args[0] in ["c", "channel"]:
            to_roll = [user async for user in self.get_users_in_voice(ctx)]
        
        elif len(args)>1:
            to_roll = list(args)
        
        choice = random.choice(to_roll)
        
        await ctx.send(choice)
        

    # UNFINISHED!
    @commands.command(name="removebg")
    async def remove_bg(self, ctx: commands.Context, image_url: str=None) -> None:
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

        try:
            # Use my bad algorithm that fails about once every every 10000 attempts
            # for random resolutions 425-2000 * 425-2000
            new_w, new_h = await self.smart_resize(width, height)
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

    async def smart_resize(self, width, height) -> None:
        """
        Spoiler alert: Not very smart, but better than brute-force 
        resizing every multiple of 1-16"""
        TARGET_SIZE = 240_000
        max_diff = TARGET_SIZE * 0.02

        async def almost_equal(img_size: int, target_size: int, threshold: int=math.ceil(max_diff/1000) * 1000) -> bool:
            if img_size > target_size:
                diff = img_size - target_size
            else:
                diff = target_size - img_size
            return diff < threshold

        async def resize(width, height, target, n=1):
            new = width//n * height//n
            if not await almost_equal(new, target) or new > target:
                if new > target:
                    n += 0.1
                    return await resize(width, height, target, n)
                if target > new:
                    n -= 0.01
                    return await resize(width, height, target, n)
            return n
    
        new = width * height
        if new > TARGET_SIZE:
            _n = (new / TARGET_SIZE)
            width, height = width*_n, height*_n
        
        n = await resize(width, height, TARGET_SIZE, n=1)

        return int(abs(width//n)), int(abs(height//n))
