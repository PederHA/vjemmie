import random
from asyncio import coroutine
from functools import partial
from pathlib import Path
from typing import Dict, List, Optional, Union

import discord
import markovify
from aiofile import AIOFile
from discord.ext import commands
from markovify import NewlineText

from ..utils.commands import add_command
from .base_cog import BaseCog


async def gpt_command(cls: commands.Cog, ctx: commands.Context, *, path: str=None, n_lines: Optional[int]=None) -> None:
    if not path:
        raise ValueError("No path lol")

    if not n_lines:
        line = await cls.random_line_from_gptfile(path)
        await ctx.send(line)
    else:
        lines = "".join(
            [await cls.random_line_from_gptfile(path) for n in range(n_lines)]
        )
        await cls.send_text_message(lines, ctx)
    

class MemeCog(BaseCog):
    """Text meme commands"""

    EMOJI = ":spaghetti:"
    
    def __init__(self, bot) -> None:
        super().__init__(bot)
        self.experimental = False
        self.wordlist: List[str] = []
        self.models: Dict[str, NewlineText] = {}
        self.daddy_verbs = self.load_daddy_verbs()
        self.files: Dict[str, List[str]] = {}
        self.create_gpt_commands()

    def create_gpt_commands(self) -> None:
        for file_ in Path("memes/txt/gpt").iterdir():
            if file_.suffix != ".txt":
                continue
            
            add_command(self, 
                        gpt_command, 
                        name=file_.stem, 
                        group=self.gpt, 
                        path=str(file_), # command kwargs
                        n_lines=10
                        )

    def load_daddy_verbs(self) -> List[str]:
        """NOTE: Blocking!"""
        try:
            with open("memes/txt/verbs.txt", "r", encoding="utf-8") as f:
                return f.read().splitlines()
        except:
            print("Failed to load 'memes/txt/verbs.txt'")
            self.verb_me_daddy.enabled = False # Disable command
            return list()
    
    async def random_line_from_gptfile(self, path: str, encoding: str="utf-8", **kwargs) -> str:
        """Kinda primitive rn. Needs some sort of caching for bigger files."""
        if path not in self.files:
            async with AIOFile(path, "r", encoding=encoding, **kwargs) as f:
                self.files[path] = (await f.read()).split("====================")
        return random.choice(self.files[path])
    
    @commands.group(name="gpt")
    async def gpt(self, ctx: commands.Context) -> None:
        if not ctx.invoked_subcommand:
            await ctx.invoke(self.bot.get_command("help"), "gpt")

    @commands.command(name="goodshit")
    async def goodshit(self, ctx: commands.Context) -> None:
        """👌👀👌👀👌👀👌👀👌👀"""
        await self.read_send_file(ctx, "memes/txt/goodshit.txt")

    @commands.command(name="mason")
    async def mason(self, ctx: commands.Context) -> None:
        "DOTA ALL STAR..."
        await self.read_send_file(ctx, "memes/txt/mason.txt")

    @commands.command(name="madara")
    async def madara(self, ctx: commands.Context) -> None:
        """Is there a character..."""
        await self.read_send_file(ctx, "memes/txt/madara.txt")

    @commands.command(name="goodmorning")
    async def goodmorning(self, ctx: commands.Context, experimental: bool=False) -> None:
        if not self.wordlist or experimental != self.experimental:
            if experimental:
                fp = "memes/txt/6of12.txt"
                self.experimental = True
            else:
                fp = "memes/txt/nationalities.txt"
                self.experimental = False

            async with AIOFile(fp, "r") as f:
                self.wordlist = (await f.read()).splitlines()
            
        word = random.choice(self.wordlist)
        
        await ctx.send(f"Good morning to everyone apart from the {word}")

    @commands.command(name="daddy")
    async def verb_me_daddy(self, ctx: commands.Context) -> None:
        verb = random.choice(self.daddy_verbs).capitalize()
        await ctx.send(f"{verb} me daddy")

    @commands.command(name="emojipastam")
    async def emojipasta_markovchain(self, ctx: commands.Context) -> None:
        subreddit = "emojipasta"
        
        if subreddit not in self.models:
            reddit_cog = self.bot.get_cog("RedditCog")
            
            posts = await reddit_cog.get_from_reddit(ctx, subreddit, is_text=True, rtn_posts=True)
            text = "\n".join([post.selftext for post in posts if post.selftext])
            model = markovify.NewlineText(text)
            
            self.models[subreddit] = model
        else:
            model = self.models.get(subreddit)
        
        await ctx.send(model.make_sentence(tries=300))
        
    @commands.command(name="ricardo")
    async def ricardo(self, ctx: commands.Context, limit: int=4176) -> None:
        """Get random submission from ricardodb.tk. 
        
        Limit is hard-coded right now because parsing the content on the site
        is a bit of a pain, and additionally their SSL certificate is not recognized
        by the `certifi` module."""
        n = random.randint(1, limit)
        await ctx.send(f"https://ricardodb.tk/post/{n}")
