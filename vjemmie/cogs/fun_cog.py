import asyncio
import io
import math
import random
import traceback
import unicodedata
from functools import partial
from itertools import chain
from pprint import pprint
from typing import Union

import discord
import numpy as np
import unidecode
from discord.ext import commands
from mwthesaurus import MWClient

from ..utils.exceptions import CommandError
from ..utils.messaging import fetch_message
from .base_cog import BaseCog

mw: MWClient = None

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
            
    @commands.command(name='random', usage="<name1>, <name2>, ..., [namelast]")
    async def roll2(self, ctx: commands.Context, *args) -> None:
        """
        Select randomly from `<name1>, <name2>, ..., [namelast]`.
        At least two names must be specified.
        """    
        # Parse args
        if args and args[0] in ["c", "channel"]:
            to_roll = await self.get_usernames_in_voice_channel(ctx)
        elif len(args)>1:
            to_roll = list(args)          
        else:
            raise CommandError("At least two items separated by spaces are required!")       
        
        await ctx.send(random.choice(to_roll))
    
    @commands.command(name="braille", usage="<text>")
    async def braille(self, ctx: commands.Context, *text: str) -> None:
        """Braille transliteration."""
        text = " ".join(text)
        trans = await self.transliterate_braille(text)
        await ctx.send(trans)

    async def transliterate_braille(self, text: str) -> str:
        """Public braille transliteration method other cogs can use."""
        return await self._do_transliterate(text.casefold(), BRAILLE_MAPPING)

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
        
        trans = await self.transliterate_uwu(to_trans)

        _iw = ctx.invoked_with
        owo = f"{_iw[0].capitalize()}{_iw[1]}{_iw[2].capitalize()}"
        await ctx.send(f"{trans} {owo}")

    async def transliterate_uwu(self, text: str) -> str:
        """Public UwU transliteration method other cogs can use."""
        return await self._do_transliterate(text, UWU_MAPPING)

    async def _do_transliterate(self, text: str, mapping: dict) -> str:     
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

    @commands.command(name="emojis", usage="<emoji> <phrase>")
    async def emojis(self, ctx:commands.Context, emoji: str=None, *text: str) -> None:
        """👏VJEMMIE👏IS👏A👏BOT👏"""
        if not emoji:
            return await ctx.send("Emoji is a required argument")
        
        if not text:
            return await ctx.send("Text is a required argument")
        
        # Split words if text arg is provided as quoted string
        if len(text) == 1:
            text = text[0].split(" ")

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

    @commands.command(name="big", aliases=["regional_indicator"])
    async def regional_indicator_text(self, ctx: commands.Context, *text) -> None:
        """BIG TEXT."""
        text = " ".join(text)
        if not text:
            raise CommandError("Can't bigify an empty string!")
        elif all(not c.isalpha() for c in text):
            raise CommandError("Can't bigify a string of non-alphabetic characters!")   
        
        try:
            big_text = await self.big_text(text)
        except:
            raise CommandError("Unable to bigify string!")
        
        if not big_text:
            raise CommandError("None of the characters in the string could be bigified!")
        
        await ctx.send(big_text)

    async def big_text(self, text: str) -> str:
        """Replaces characters in a string with regional indicator emojis."""
        t = []
        chars = "".join([unidecode.unidecode(c) for c in text.casefold()])  
        for c in chars:                # normalize to ascii char (æ -> ae)
            # Letters
            if c.isalpha() and ord(c) < 128:
                t.append(f":regional_indicator_{c}:")
            # Numbers
            elif c.isdigit():
                name = unicodedata.name(c).split(" ")[1].lower()
                t.append(f":{name}:")
            # Symbols
            else:
                if c.isspace():
                    c = c*2 # Double spacing
                t.append(c)
        return "".join(t)
    
    @commands.command(name="team")
    async def split(self, ctx: commands.Context, n_teams: int=2, *ignored) -> None:
        """Split users in a voice channel into 2 or more teams."""
        if n_teams < 2:
            raise CommandError("Cannot split into less than 2 teams!")
        
        users = [
            user for user 
            in await self.get_usernames_in_voice_channel(ctx)
            if user not in ignored
        ]

        if len(users) <= 2:
            raise CommandError("More than 2 players are required to generate teams!")
        elif len(users) < n_teams:
            raise CommandError("Number of teams cannot exceed number of users!")
        
        random.shuffle(users)
        teams_ = list(np.array_split(users, n_teams))
        
        # Create message
        n = "\n" # backslashes aren't allowed in f-strings
        teams = "\n".join(
            [
            f"Team {i}\n```{n.join([f'* {user}' for user in team])}```" 
            for i, team in list(enumerate(teams_, start=1))
            ]
        )
        await self.send_embed_message(ctx, title="Teams", description=teams)        

    @commands.command(name="synonyms", aliases=["syn"])
    async def word_synonyms(self, ctx: commands.Context, word: str) -> None:
        try:
            definition = await mw.aget(word.lower())
        except ValueError:
            return await ctx.send(f"No definition found for **{word}**.")
        except AttributeError:
            return await ctx.send(f"Unable to fetch synonyms for {word}")
        
        synonyms = chain.from_iterable(word.synonyms for word in definition)
        if not synonyms:
            return await ctx.send("Word has no synonyms!")
        
        synstr = ", ".join(synonyms)
        await self.send_text_message(f"**{word.capitalize()}** synonyms:\n{synstr}", ctx)

    @commands.command(name="timer")
    async def timer(self, ctx: commands.Context, minutes: int) -> None:
        if minutes <= 0:
            raise CommandError("Sleep duration cannot be 0 minutes or less.")
        self.bot.loop.create_task(self._timer(ctx, minutes))

    async def _timer(self, ctx: commands.Context, minutes: int) -> None:
        await ctx.send(f"Timer started for {minutes} minute{'s' if minutes > 1 else ''}")
        await asyncio.sleep(minutes*60)
        await ctx.send(f"Timer ended after {minutes} minutes {ctx.message.author.mention}")