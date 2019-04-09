import asyncio
import random
import traceback
import io
from pprint import pprint
from functools import partial
import math

import discord
from discord.ext import commands

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
