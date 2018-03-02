from discord.ext import commands
import discord
from ext_module import ExtModule
import random
import praw
import asyncio
import re
import secrets

reddit = praw.Reddit(client_id=secrets.REDDIT_ID,
                     client_secret=secrets.REDDIT_SECRET,
                     user_agent=secrets.REDDIT_USER_AGENT,
                    )

class RedditCog:
    """PUBG Bot Commands
    """
    def __init__(self, bot: commands.Bot, log_channel_id: int=None):
        """The constructor of the UserCog class, assigns the important variables
        Args:
            bot: The bot the commands will be added to (commands.Bot)
            log_channel_id: The id of the log_channel (int)
        """
        self.bot = bot
        self.log_channel_id = log_channel_id
        self.send_log = None                # will be assigned
        self.bot.remove_command('help')
    
    async def on_ready(self):
        """Is called when the bot is completely started up. Calls in this function need variables only a started bot can give.
        """
        self.send_log = ExtModule.get_send_log(self)
    
    @commands.command()
    async def emojipasta(self, ctx: commands.Context, *args: str):
        sub = reddit.subreddit('emojipasta')
        posts = sub.top(limit=400) 
        random_post_number = random.randint(1,400)
        print (random_post_number)
        for i,post in enumerate(posts):
            if i==random_post_number:
                print (i)
                print (random_post_number)
                if post.selftext != None:
                    print(post.selftext)
                    return await ctx.send(post.selftext)
                elif post.selftext == None:
                    print (post.title)
                

    @commands.command()
    async def ipfb(self, ctx: commands.Context, *args: str):
        sub = reddit.subreddit('indianpeoplefacebook')
        posts = sub.top(limit=400) 
        random_post_number = random.randint(1,400)
        print (random_post_number)
        for i,post in enumerate(posts):
            if i==random_post_number:
                print (i)
                print (random_post_number)
                if post.selftext != None:
                    print(post.selftext)
                    return await ctx.send(post.url)
                elif post.selftext == None:
                    print (post.title)

    @commands.command()
    async def spt(self, ctx: commands.Context, *args: str):
        sub = reddit.subreddit('scottishpeopletwitter')
        posts = sub.top(limit=400) 
        random_post_number = random.randint(1,400)
        print (random_post_number)
        for i,post in enumerate(posts):
            if i==random_post_number:
                print (i)
                print (random_post_number)
                if post.selftext != None:
                    print(post.selftext)
                    return await ctx.send(post.url)
                elif post.selftext == None:
                    print (post.title)

    @commands.command(help="Accepted args: \"week, month, year\"",brief="Edgy memes",aliases=["dm", "2edgy4me"])
    async def dankmemes(self, ctx: commands.Context, *args: str):
        sub = reddit.subreddit('dankmemes')
        aArgs = ['week', 'month', 'year']
        if args != ():
            for a in aArgs:
                #print ("{}".format(a))
                if ("{}".format(a)) == args[0]:
                    sargs = str("{}".format(a))
                    posts = sub.top(time_filter=sargs, limit=100)
                    random_post_number = random.randint(1,100)            
        else:
            posts = sub.top(limit=400)
            random_post_number = random.randint(1,400)
        print(random_post_number)
        for i,post in enumerate(posts):
            if i==random_post_number:
                return await ctx.send("**" + post.title + "**" +"\n" + post.url)

    @commands.command()
    async def dfm(self, ctx: commands.Context, *args: str):
        sub = reddit.subreddit('deepfriedmemes')
        posts = sub.top(limit=400) 
        random_post_number = random.randint(1,400)
        print (random_post_number)
        for i,post in enumerate(posts):
            if i==random_post_number:
                print (i)
                print (random_post_number)
                if post.selftext != None:
                    print(post.selftext)
                    return await ctx.send(post.url)
                elif post.selftext == None:
                    print (post.title)

    @commands.command()
    async def ept(self, ctx: commands.Context, *args: str):
        sub = reddit.subreddit('emojipasta')
        posts = sub.top(limit=200) 
        random_post_number = random.randint(1,200)
        print (random_post_number)
        for i,post in enumerate(posts):
            if i==random_post_number:
                print (i)
                print (random_post_number)
                print(post.title)
                return await ctx.send(post.title)

    @commands.command()
    async def copypasta(self, ctx: commands.Context, *args: str):
        sub = reddit.subreddit('copypasta')
        posts = sub.top(limit=200) 
        random_post_number = random.randint(1,200)
        print (random_post_number)
        for i,post in enumerate(posts):
            if i==random_post_number:
                print (i)
                print (random_post_number)
                print(post.selftext)
                return await ctx.send(post.selftext)