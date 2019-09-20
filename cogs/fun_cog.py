import asyncio
import io
import math
import random
import traceback
import re
import unicodedata
from functools import partial
from pprint import pprint
from typing import Union

import discord
import requests
from discord.ext import commands

from cogs.base_cog import BaseCog
from utils.exceptions import CommandError
from utils.messaging import fetch_message

# Translations are defined strictly in lower-case
UWU_MAPPING = {
    "fuck": "fack",
    "ath": "aff",
    "eth": "eff",
    "ith": "iff",
    "oth": "off",
    "uth": "uff",
    "they": "deyy",
    "the": "dee",
    "r": "w",
    "l": "w"
}

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
        text = text.casefold()
        re.search(r"([a-z0-9,.!? ]+)", text)
        return self._do_transliterate(text, BRAILLE_MAPPING)

    @commands.command(name="uwu", aliases=["owo"], usage="<message string> or <message_ID>")
    async def uwu(self, ctx: commands.Context, *args) -> None:
        """UwU-style transliteration"""
        arg = " ".join(args)
        
        # Try to fetch message if arg is a number
        if arg.isdigit():
            msg = await fetch_message(ctx, arg)
            to_trans = msg.content
        else:
            to_trans = arg
        
        if not to_trans:
            raise CommandError("No string to transliterate.")
        
        trans = self.do_uwu_transliterate(to_trans)

        _iw = ctx.invoked_with
        owo = f"{_iw[0].capitalize()}{_iw[1]}{_iw[2].capitalize()}"
        await ctx.send(f"{trans} {owo}")

    def do_uwu_transliterate(self, text: str) -> str:
        """Public UwU transliteration method other cogs can use."""
        return self._do_transliterate(text, UWU_MAPPING)

    def _do_transliterate(self, text: str, mapping: dict) -> str:     
        # Get capitalization of each character in string
        caps = []
        for char in text:
            caps.append(1 if char.isupper() else 0)
        
        # Fold case of string before transliterating
        text = text.casefold()

        # Replace characters with those in mapping
        for k, v in mapping.items():
            text = text.replace(k, v)
        
        # Transliterate 1 word at the time
        s = []
        word = []
        for cap, char in zip(caps, text):
            if cap:
                char = char.upper()
            if not char.isspace():
                word.append(char)
            else:
                s.append(word)
                word = [] 
        else:
            s.append(word)
        
        # Join words
        trans = " ".join(["".join(w) for w in s])
        
        return trans

    @commands.command(name="emojis")
    async def emojis(self, ctx:commands.Context, emoji: str=None, *text: str) -> None:
        """Replace spaces in a string with emojis."""
        if not emoji:
            return await ctx.send("Emoji is a required argument")
        
        if not text:
            return await ctx.send("Text is a required argument")
        
        out = f"{emoji}{emoji.join(list(text))}{emoji}"

        await ctx.send(out)

    @commands.command(name="sheriff")
    async def sheriff(self, ctx: commands.Context, emoji: str) -> None:
        """Make a sheriff out of emojis."""
        out = """
        \n⁯⁯⁯⁯ 
⠀ ⠀ ⠀    🤠
　   {e}{e}{e}
    {e}   {e}　{e}
    👇  {e}{e} 👇
  　  {e}　{e}
　   {e}　 {e}
　   👢     👢
    """.format(e=emoji)
        try:
            emoji_name = unicodedata.name(emoji)
        except:
            if ":" in emoji:
                emoji_name = emoji.split(":", 3)[1]
            else:
                emoji_name = None
        if emoji_name is not None:
            out += f"\nI am the sheriff of {emoji_name.title()}"
        await ctx.send(out)