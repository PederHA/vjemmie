from discord.ext import commands
import discord
from ext_module import ExtModule
import random
import praw
import asyncio
import re
import secrets
import traceback

reddit = praw.Reddit(
    client_id=secrets.REDDIT_ID,
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
    More precise tuning of results. (Top All-time/Year/Month/Week)

    Filtering for type of result when using the ``!reddit`` command. (img/txt)

    """

    def __init__(self, bot: commands.Bot, log_channel_id: int = None):
        self.bot = bot
        self.log_channel_id = log_channel_id
        self.send_log = None
        self.ALL_POST_LIMIT = 250
        self.OTHER_POST_LIMIT = 100
        self.image_extensions = [".jpg", ".png", ".gif"]
        self.image_hosts = ["imgur.com", "i.redd.it"]
        self.time_filters = ["all", "year", "month", "week", "day"]
        self.sorting_filters = ["hot", "top"]

    async def on_ready(self):
        """Is called when the bot is completely started up. Calls in this function need variables only a started bot can give.
        """
        self.send_log = ExtModule.get_send_log(self)

    @commands.command()
    async def emojipasta(self, ctx: commands.Context, *args: str):
        subreddit = "emojipasta"
        postlimit = self.ALL_POST_LIMIT
        sub_type = "txt"

        await self.random_post(ctx.message, subreddit, postlimit, sub_type, args)

    @commands.command()
    async def ipfb(self, ctx: commands.Context, *args: str):
        subreddit = "indianpeoplefacebook"
        postlimit = self.ALL_POST_LIMIT
        sub_type = "img"

        await self.random_post(ctx.message, subreddit, postlimit, sub_type, args)

    @commands.command()
    async def spt(self, ctx: commands.Context, *args: str):
        subreddit = "scottishpeopletwitter"
        postlimit = self.ALL_POST_LIMIT
        sub_type = "img"

        await self.random_post(ctx.message, subreddit, postlimit, sub_type, args)

    @commands.command(
        help='Valid args: "week, month, year"',
        brief="Edgy memes",
        aliases=["dm", "2edgy4me"],
    )
    async def dankmemes(self, ctx: commands.Context, *args: str):
        subreddit = "dankmemes"
        postlimit = self.ALL_POST_LIMIT
        sub_type = "img"

        await self.random_post(ctx.message, subreddit, postlimit, sub_type, args)

    @commands.command(aliases=["dfm"])
    async def deepfriedmemes(self, ctx: commands.Context, *args: str):
        subreddit = "deepfriedmemes"
        postlimit = self.ALL_POST_LIMIT
        sub_type = "img"

        await self.random_post(ctx.message, subreddit, postlimit, sub_type, args)

    @commands.command()
    async def copypasta(self, ctx: commands.Context, *args: str):
        subreddit = "copypasta"
        postlimit = self.ALL_POST_LIMIT
        sub_type = "txt"

        await self.random_post(ctx.message, subreddit, postlimit, sub_type, args)

    @commands.command(aliases=["mmirl", "mmi"])
    async def metal_me_irl(self, ctx: commands.Context, *args: str):
        subreddit = "metal_me_irl"
        postlimit = self.ALL_POST_LIMIT
        sub_type = "img"

        await self.random_post(ctx.message, subreddit, postlimit, sub_type, args)

    @commands.command()
    async def reddit(self, ctx: commands.Context, *args):
        if len(args) >= 1:
            subreddit = args[0]
            postlimit = self.ALL_POST_LIMIT
            sub_type = "img"

            await self.random_post(ctx.message, subreddit, postlimit, sub_type, args)
        else:
            await ctx.send("No subreddit provided. Usage: !reddit [subreddit]")

    async def random_post(self, ctx, subreddit, postlimit: int, sub_type, args):
        """
        Calls 1 of 2 methods; ``img_subreddit()`` or ``txt_subreddit()``,
        and sends return value to the channel the command was invoked in.

        Arguments:
            ctx: message object passed from the subreddit bot command. (ctx.message)
            subreddit: Name of subreddit. (str)
            postlimit (int): Number of posts to search through 1-postlimit. (int)
            sub_type: Type of subreddit - txt or img. (str)
            bot: The bot instance the cog is added to.
            args: Tuple containing optional arguments for time filter and content filter (hot/top)
        """

        channel = self.bot.get_channel(ctx.channel.id)

        args = list(args)

        if len(args) > 1:
            for sf in self.sorting_filters:
                for arg in args:
                    if sf == arg:
                        sorting_filter = arg
                        break
        else:
            sorting_filter = "hot"

        if len(args) > 2:
            for tf in self.time_filters:
                for arg in args:
                    if tf == arg:
                        time_filter = arg
                        break
        else:
            time_filter = "all"

        try:
            if sub_type == "txt":
                post = await self.txt_subreddit(
                    subreddit, postlimit, sorting_filter, time_filter
                )
            elif sub_type == "img":
                post = await self.img_subreddit(
                    subreddit, postlimit, sorting_filter, time_filter
                )
            await channel.send(post)
        except:
            error = traceback.format_exc()
            await RedditCog.send_error(self, error)

            if "Must be 2000 or fewer in length." in error:
                await channel.send("The reddit post exceeded Discord's character limit")
            else:
                await channel.send("An unexpected error occured.")

    async def txt_subreddit(self, subreddit, postlimit: int, sorting_filter, time_filter):
        if sorting_filter == "top":
            sub = reddit.subreddit(subreddit)
            posts = sub.top(time_filter=time_filter, limit=postlimit)
            random_post_number = random.randint(1, postlimit)

        elif sorting_filter == "hot":
            sub = reddit.subreddit(subreddit)
            posts = sub.hot()
            random_post_number = random.randint(1, 25)

        try:
            for i, post in enumerate(posts):
                if i == random_post_number:
                    if post.selftext != "":
                        return post.selftext
                    else:
                        if (post.url[-4:] in self.image_extensions) or (
                            post.url in self.image_hosts
                        ):
                            post = post.title + "\n" + post.url
                            return post
                        else:
                            return post.title
                    break
        except:
            error = traceback.format_exc()
            await RedditCog.send_error(self, error)

    async def img_subreddit(
        self, subreddit, postlimit: int, sorting_filter, time_filter
    ):
        if sorting_filter == "top":
            sub = reddit.subreddit(subreddit)
            posts = sub.top(time_filter=time_filter, limit=postlimit)
            random_post_number = random.randint(1, postlimit)

        elif sorting_filter == "hot":
            sub = reddit.subreddit(subreddit)
            posts = sub.hot()
            random_post_number = random.randint(1, 25)

        try:
            for i, post in enumerate(posts):
                if i == random_post_number:
                    post = "**" + post.title + "**\n" + post.url
                    return post
        except:
            error = traceback.format_exc()
            await RedditCog.send_error(self, error)
            return "An unexpected error occured."

    async def send_error(self, error):
        channel = self.bot.get_channel(340921036201525248)
        await channel.send(str(error))
