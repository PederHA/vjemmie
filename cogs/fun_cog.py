import asyncio
import io
import math
import random
import traceback
from functools import partial
from pprint import pprint
from typing import Union

import discord
import requests
from discord.ext import commands

from cogs.base_cog import BaseCog
from utils.exceptions import CommandError


class FunCog(BaseCog):
    """Commands that don't fit into any other categories."""

    EMOJI = ":game_die:"

    @commands.command(name='roll',
                      aliases=['dice'],
                      description='Random roll. Provide number argument to specify range (1-100 default).')
    async def roll(self, ctx: commands.Context, lower: Union[int, str]=0, upper: Union[int, str]=100) -> None:
        """!roll 0-<high> or <low> <high>"""
        type_err = "Upper and lower bounds must be integers!"
        
        # Check if user passed in bounds as "<upper>-<lower>"
        if isinstance(lower, str) and "-" in lower:
            lower, upper = lower.split("-")
            try:
                lower, upper = int(lower), int(upper)
            except ValueError:
                raise CommandError(type_err)
        
        # Raise exception if lower or upper bound is str
        if isinstance(lower, str) or isinstance(upper, str):
            raise CommandError(f"{type_err}. Did you mean **`!random`**?")
        
        await ctx.send(random.randint(lower, upper))
            
    @commands.command(name='random')
    async def roll2(self, ctx: commands.Context, *args) -> None:
        """
        Select from  <item1, item2, ..., itemlast>
        """    
        # Parse args
        if args and args[0] in ["c", "channel"]:
            to_roll = [user async for user in self.get_users_in_voice(ctx)]
        elif len(args)>1:
            to_roll = list(args)          
        else:
            raise CommandError("At least two items separated by spaces are required!")       
        
        await ctx.send(random.choice(to_roll))
    
    @commands.command(name="braille")
    async def braille(self, ctx: commands.Context, *text: str) -> None:
        """Braille transliteration."""
        char_map = {
            'a': '⠁',
            'b': '⠃',
            'c': '⠉',
            'd': '⠙',
            'e': '⠑',
            'f': '⠋',
            'g': '⠛',
            'h': '⠓',
            'i': '⠊',
            'j': '⠚',
            'k': '⠅',
            'l': '⠇',
            'm': '⠍',
            'n': '⠝',
            'o': '⠕',
            'p': '⠏',
            'q': '⠟',
            'r': '⠗',
            's': '⠎',
            't': '⠞',
            'u': '⠥',
            'v': '⠧',
            'x': '⠭',
            'y': '⠽',
            'z': '⠵',
            'w': '⠺',
            " ": " "
        }
        translation = str.maketrans(char_map)
        text = " ".join(text).lower()
        await ctx.send(text.translate(translation))
