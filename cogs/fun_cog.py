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


# Translations are defined strictly in lower-case
UWU_MAPPING = {
    "fuck": "fack",
    "ath": "af",
    "eth": "ef",
    "ith": "if",
    "oth": "of",
    "uth": "uf",
    "they": "dey",
    "the": "de",
    "r": "w",
    "l": "w"
}
# Upper-case translations
UWU_MAPPING.update({k.upper(): v.upper() for k, v in UWU_MAPPING.items()})
# Mixed-case translation
UWU_MAPPING.update({k[0].upper()+k[1:]: v[0].upper()+v[1:] for k, v in UWU_MAPPING.items() if len(k)>1})

BRAILLE_MAPPING = {
    "a": "⠁",
    "b": "⠃",
    "c": "⠉",
    "d": "⠙",
    "e": "⠑",
    "f": "⠋",
    "g": "⠛",
    "h": "⠓",
    "i": "⠊",
    "j": "⠚",
    "k": "⠅",
    "l": "⠇",
    "m": "⠍",
    "n": "⠝",
    "o": "⠕",
    "p": "⠏",
    "q": "⠟",
    "r": "⠗",
    "s": "⠎",
    "t": "⠞",
    "u": "⠥",
    "v": "⠧",
    "x": "⠭",
    "y": "⠽",
    "z": "⠵",
    "w": "⠺",
    "0": "⠼⠚",
    "1": "⠼⠁",
    "2": "⠼⠃",
    "3": "⠼⠉",
    "4": "⠼⠙",
    "5": "⠼⠑",
    "6": "⠼⠋",
    "7": "⠼⠛",
    "8": "⠼⠓",
    "9": "⠼⠊"
}

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
    
    @commands.command(name="braille", usage="<text>")
    async def braille(self, ctx: commands.Context, *text: str) -> None:
        """Braille transliteration."""
        text = " ".join(text)
        trans = self.do_braille_transliterate(text)
        await ctx.send(trans)

    def do_braille_transliterate(self, text: str) -> str:
        """Public braille transliteration method other cogs can use."""
        text = text.lower()
        return self._do_transliterate(text, BRAILLE_MAPPING)

    @commands.command(name="uwu", aliases=["owo"], usage="<message string> or <message_ID>")
    async def uwu(self, ctx: commands.Context, *args) -> None:
        """UwU-style transliteration"""
        arg = " ".join(args)
        
        # Try to fetch message if arg is a number
        if arg.isnumeric():
            try:
                msg = await ctx.fetch_message(arg)
            except discord.NotFound:
                raise CommandError("Invalid message ID!")
            except discord.Forbidden:
                raise CommandError("Lacking permissions to fetch message!")
            except discord.HTTPException:
                raise CommandError("Failed to retrieve message. Try again later!")
            else:
                to_trans = msg.content
        else:
            to_trans = arg
        
        trans = self.do_uwu_transliterate(to_trans)

        await ctx.send(trans)

    def do_uwu_transliterate(self, text: str) -> str:
        """Public UwU transliteration method other cogs can use."""
        return self._do_transliterate(text, UWU_MAPPING)

    def _do_transliterate(self, text: str, mapping: dict) -> str:
        for k, v in mapping.items():
            text = text.replace(k, v)  
        return text 
