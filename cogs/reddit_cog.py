from discord.ext import commands
import discord
from ext_module import ExtModule
import random
import praw
import asyncio
import re
import secrets
import traceback

reddit = praw.Reddit(client_id=secrets.REDDIT_ID,
                     client_secret=secrets.REDDIT_SECRET,
                     user_agent=secrets.REDDIT_USER_AGENT,
                    )

class RedditCog:
    """
    Reddit cog.
    ====
    Each subreddit is divided into its own command.

    For example:
    ----
    ``!spt`` or ``!emojipasta``

    TODO:
    ----
    Add ``!reddit`` command that allows for any subreddit.
    However, a more generalized function is needed for that.
    
    """

    def __init__(self, bot: commands.Bot, log_channel_id: int=None):
        self.bot = bot
        self.log_channel_id = log_channel_id
        self.send_log = None               
        self.ALL_POST_LIMIT = 400
        self.OTHER_POST_LIMIT = 100
        self.image_extensions = [".jpg",".png",".gif"]
        self.image_hosts =["imgur.com", "i.redd.it"]
    
    async def on_ready(self):
        """Is called when the bot is completely started up. Calls in this function need variables only a started bot can give.
        """
        self.send_log = ExtModule.get_send_log(self)
    

    @commands.command()
    async def emojipasta(self, ctx: commands.Context, *args: str):
        subreddit = "emojipasta"
        postlimit = self.ALL_POST_LIMIT
        sub_type = "txt"
        
        await RedditCog.random_post(self,ctx.message,subreddit,postlimit, sub_type,self.bot)

    @commands.command()
    async def ipfb(self, ctx: commands.Context, *args: str):
        subreddit = "indianpeoplefacebook"
        postlimit = self.ALL_POST_LIMIT
        sub_type = "img"

        await RedditCog.random_post(self,ctx.message,subreddit,postlimit, sub_type,self.bot)

    @commands.command()
    async def spt(self, ctx: commands.Context, *args: str):
        subreddit = "scottishpeopletwitter"
        postlimit = self.ALL_POST_LIMIT
        sub_type = "img"

        await RedditCog.random_post(self,ctx.message,subreddit,postlimit, sub_type,self.bot)

    @commands.command(help="Valid args: \"week, month, year\"",brief="Edgy memes",aliases=["dm", "2edgy4me"])
    async def dankmemes(self, ctx: commands.Context, *args: str):
        subreddit = "dankmemes"
        postlimit = self.ALL_POST_LIMIT
        sub_type = "img"

        await RedditCog.random_post(self,ctx.message,subreddit,postlimit, sub_type,self.bot)

    @commands.command(aliases=["dfm"])
    async def deepfriedmemes(self, ctx: commands.Context, *args: str):
        subreddit = "deepfriedmemes"
        postlimit = self.ALL_POST_LIMIT
        sub_type = "img"

        await RedditCog.random_post(self,ctx.message,subreddit,postlimit, sub_type,self.bot)

    @commands.command()
    async def copypasta(self, ctx: commands.Context, *args: str):
        subreddit = "copypasta"
        postlimit = 200
        sub_type = "txt"
        
        await RedditCog.random_post(self,ctx.message,subreddit,postlimit, sub_type,self.bot)
    
    async def random_post(self, ctx, subreddit, postlimit: int, sub_type, bot):
        """
        Calls 1 of 2 methods; ``img_subreddit()`` or ``txt_subreddit()``,
        and sends return value to the channel the command was invoked in.
        
        Arguments:
            ctx: message object passed from the subreddit bot command. (ctx.message)
            subreddit: Name of subreddit. (str)
            postlimit (int): Number of posts to search through 1-postlimit. (int)
            sub_type: Type of subreddit - txt or img. (str)
            bot: The bot instance the cog is added to.
        """

        self.bot = bot
        channel = self.bot.get_channel(ctx.channel.id)

        try:
            if sub_type == "txt":
                post = await RedditCog.txt_subreddit(self,subreddit,postlimit)
            elif sub_type == "img":
                post = await RedditCog.img_subreddit(self,subreddit,postlimit)
            await channel.send(post)
        except:
            error = traceback.format_exc()
            await RedditCog.send_error(self,error)

            if "Must be 2000 or fewer in length." in error:
                await channel.send("The reddit post exceeded Discord's character limit")
            else:
                await channel.send("An unexpected error occured.")
    
    async def txt_subreddit(self,subreddit, postlimit: int):
        sub = reddit.subreddit(subreddit)
        posts = sub.top(limit=postlimit)
        random_post_number = random.randint(1,postlimit)

        try:
            for i,post in enumerate(posts):
                if i==random_post_number:
                    if post.selftext != '':
                        return post.selftext
                    else:
                        if (post.url[-4:] in self.image_extensions) or (post.url in self.image_hosts): 
                            post = post.title + "\n" +  post.url
                            return post
                        else:
                            return post.title
                    break
        except:
            error = traceback.format_exc()
            await RedditCog.send_error(self,error)

    async def img_subreddit(self,subreddit, postlimit: int):
        sub = reddit.subreddit(subreddit)
        posts = sub.top(limit=postlimit)
        random_post_number = random.randint(1,postlimit)

        try:
            for i,post in enumerate(posts):
                if i==random_post_number:
                    post = "**" + post.title + "**\n" + post.url
                    return post
        except:
            error = traceback.format_exc()
            await RedditCog.send_error(self,error)
            return "An unexpected error occured."

    
    async def send_error(self, error):
        channel = self.bot.get_channel(340921036201525248)
        await channel.send(str(error))