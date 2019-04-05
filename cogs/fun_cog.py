import asyncio
import random
import traceback
from pprint import pprint

import discord
import aiohttp
from discord.ext import commands

from cogs.base_cog import BaseCog
from botsecrets import REMOVEBG_API_KEY


class FunCog(BaseCog): 
    @commands.command(name='roll',
                      aliases=['dice'],
                      description='Random roll. Provide number argument to specify range (1-100 default).')
    async def roll(self, ctx: commands.Context, lower: int=0, upper: int=100) -> None:
        """!roll <range>"""      
        if not isinstance(lower, int) or not isinstance(upper, int):
            return await ctx.send("Arguments must be integers!")
        
        await ctx.send(random.randint(lower, upper))
            
    @commands.command(name='random')
    async def roll2(self, ctx: commands.Context, *args) -> None:
        """
        Select from  <thing1, thing2, ..., thinglast>
        """
        if args[0] in ["c", "channel"]:
            to_roll = list(await self.get_users_in_voice(ctx))
        
        elif len(args)>1:
            to_roll = list(args)
        
        choice = random.choice(to_roll)
        
        await ctx.send(choice)
        

    # UNFINISHED!
    @commands.command(name="removebg")
    async def remove_bg(self, ctx: commands.Context, image_url: str=None) -> None:
        if not image_url and not ctx.message.attachments:
            raise discord.DiscordException("Message has image URL or image attachment")
        
        if ctx.message.attachments:
            iamge_url = ctx.message.attachments[0].url

        img = await self.download_from_url(image_url)

        # im suer this is broken im tired cba
        async with aiohttp.ClientSession() as session:
            response = await session.post(
                image_url,
                data={'image_file': img_file,
                      'size': 'auto'},
                headers={'X-Api-Key': API_KEY}
            )
        
