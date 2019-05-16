import random

import discord
from discord.ext import commands
import markovify
from cogs.base_cog import BaseCog


class MemeCog(BaseCog):
    """Text meme commands"""

    EMOJI = ":spaghetti:"
    
    def __init__(self, bot) -> None:
        super().__init__(bot)
        self.experimental = False
        self.wordlist = []
        self.models = {}
    
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
        