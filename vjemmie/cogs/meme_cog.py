import random
from typing import Optional

import discord
from discord.ext import commands
import markovify
from .base_cog import BaseCog


class MemeCog(BaseCog):
    """Text meme commands"""

    EMOJI = ":spaghetti:"
    
    def __init__(self, bot) -> None:
        super().__init__(bot)
        self.experimental = False
        self.wordlist = []
        self.models = {}
        self.daddy_verbs = self.load_daddy_verbs()
        self.files = {}
            
    def load_daddy_verbs(self) -> None:
        try:
            with open("memes/txt/verbs.txt", "r", encoding="utf-8") as f:
                return f.read().splitlines()
        except:
            print("Failed to load 'memes/txt/verbs.txt'")
            self.verb_me_daddy.enabled = False
    
    async def random_line_from_gptfile(self, path: str, encoding="utf-8", **kwargs) -> None:
        """Kinda primitive rn. Needs some sort of caching for bigger files."""
        if path not in self.files:
            with open(path, "r", encoding="utf-8", **kwargs) as f:
                self.files[path] = f.read().split("====================")
        return random.choice(self.files[path])
    
    @commands.group(name="gpt")
    async def gpt(self, ctx: commands.Context) -> None:
        if not ctx.invoked_subcommand:
            await ctx.invoke(self.bot.get_command("help"), "gpt")

    @gpt.command(name="pfm")
    async def gpt_bernie(self, ctx: commands.Context, n_lines: Optional[int]=None) -> None:
        if not n_lines:
            line = await self.random_line_from_gptfile("memes/txt/gpt/pfm.txt")
            await ctx.send(line)
        else:
            lines = "\n".join(
                [await self.random_line_from_gptfile("memes/txt/gpt/pfm.txt") for n in range(n_lines)]
            )
            await self.send_text_message(lines, ctx)
        

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

            with open(fp, "r") as f:
                self.wordlist = f.read().splitlines()
            
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
        