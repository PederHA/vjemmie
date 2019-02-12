from discord.ext import commands
import discord
from ext_module import ExtModule
import random
import praw
import asyncio
import re
import secrets
import traceback
from cogs.base_cog import BaseCog
from typing import Iterable, Tuple
import datetime
from functools import partialmethod,  partial
import pickle

reddit = praw.Reddit(
    client_id=secrets.REDDIT_ID,
    client_secret=secrets.REDDIT_SECRET,
    user_agent=secrets.REDDIT_USER_AGENT,
)

class RedditCog(BaseCog):
    ALL_POST_LIMIT = 250
    OTHER_POST_LIMIT = 100
    IMAGE_EXTENSIONS = [".jpg", ".png", ".gif"]
    IMAGE_HOSTS = ["imgur.com", "i.redd.it"]
    TIME_FILTERS = ["all", "year", "month", "week", "day"]
    SORTING_FILTERS = ["hot", "top"]
    DEFAULT_SORTING = SORTING_FILTERS[1]
    DEFAULT_TIME = TIME_FILTERS[3]
    TOP_ALL = (SORTING_FILTERS[1], TIME_FILTERS[0])

    def __init__(self, bot: commands.Bot, log_channel_id: int=None) -> None:
        super().__init__(bot, log_channel_id)
        self.subs = self.load_subs() # Load list of subs from disk
        for sub_full, sub_short in self.subs:
            self._add_sub(sub_full, sub_short)
    
    def load_subs(self) -> list:
        with open("db/subreddits.pkl", "rb") as f:
            return pickle.load(f)
    
    def dump_subs(self) -> None:
        with open("db/subreddits.pkl", "wb") as f:
            pickle.dump(self.subs, f)
    
    @commands.command(name="add_sub", aliases=["add_r", "addr", "newr", "nr"])
    async def add_sub(self, ctx: commands.Context, subreddit: str, sub_short: str="") -> None:
        try:
            self._add_sub(subreddit, sub_short)
        except discord.DiscordException:
            for sf, ss in self.subs: # full, short
                if sf == subreddit:
                    command = ss if ss else sf
                    break
            else:
                raise Exception("Fatal exception")
            await ctx.send(f"Subreddit **r/{subreddit}** already exists with command **!{command}**")
            raise
        self.dump_subs() # After adding sub, save list of subs to disk
        if not sub_short:
            sub_short = subreddit
        await ctx.send(f"Added subreddit **r/{subreddit}** with command named **!{sub_short}**")
    
    def _add_sub(self, sub_full: str, sub_short: str) -> None:
        sub_info = (sub_full, sub_short) # Create tuple of args before any modifications
        if not sub_short:
            sub_short = sub_full
        for command in self.bot.commands: # Check if subreddit is already added
            if command.name == sub_full or command.name == sub_short:
                raise discord.DiscordException("Command already exists")
        base_command = self._r # The method that is used to create custom subreddit commands
        _cmd = asyncio.coroutine(partial(base_command, subreddit=sub_full))
        cmd = commands.command(name=sub_short)(_cmd) # Use partial coroutine to create command object
        self.bot.add_command(cmd) # Add generated command to bot
        if sub_info not in self.subs:
            self.subs.append(sub_info) # Add subreddit to cog's list of subreddits
    
    async def _r(self, ctx: commands.Context, *, subreddit: str, sorting: str=None, time: str=None) -> None:
        await self.get_from_reddit(ctx, subreddit, sorting, time)
    
    @commands.command(name="remove_sub")
    async def remove_sub(self, ctx: commands.Context, subreddit: str) -> None:
        for sub_full, sub_short in self.subs:
            if sub_short == subreddit or sub_full == subreddit:
                self.subs.remove((sub_short, sub_full))
                self.bot.remove_command(sub_short)
                if not sub_full:
                    sub_full = sub_short
                await ctx.send(f"Removed subreddit **r/{sub_full}** with command named **!{sub_short}**")
                break
        self.dump_subs()
    
    @commands.command(name="subs", aliases=["subreddits"])
    async def list_subs(self, ctx: commands.Context) -> None:
        _out = []
        for sub_full, sub_short in self.subs:
            command = sub_short if sub_short else sub_full
            s = f"r/{sub_full.ljust(30)} Command: !{command}"
            _out.append(s)
        out = await self.format_output(_out, item_type="subreddits", header=True)
        await ctx.send(out)

    @commands.command(name="change_reddit_time", aliases=["rtime", "reddit_time"])
    async def change_time_filtering(self, ctx: commands.Context, time) -> None:
        time = await self.check_time(ctx,time)
        self.DEFAULT_TIME = time
        await ctx.send(f"Reddit time filtering set to **{time}**.")
    
    @commands.command(name="toggle_hot", aliases=["hot"])
    async def toggle_hot(self, ctx: commands.Context) -> None:
        if self.DEFAULT_SORTING != "hot": # At this point I have given up not hardcoding these things
            self.DEFAULT_SORTING = "hot"
        else:
            self.DEFAULT_SORTING = "top"
        await ctx.send(f"Reddit content sorting set to **{self.DEFAULT_SORTING}**")

    @commands.command(name="change_sub_command")
    async def change_sub_command(self, ctx: commands.Context, subreddit: str, command: str) -> None:
        if not command.isnumeric():
            command = command.lower()
            for sub_full, sub_short in self.subs:
                if sub_full == subreddit:
                    self.subs.remove((sub_full, sub_short))
                    self.subs.append((subreddit, command))
                    self.dump_subs()
                    await ctx.send(f"Command for subreddit **r/{subreddit}** changed to **!{command}**.\n"
                                    "Changes take effect on next restart.")
                    break
        else:
            await ctx.send("Invalid command name. Can only contain letters a-z.")
        
    @commands.command(name="reddit")
    async def reddit(self, ctx: commands.Context, subreddit: str, sorting: str=None, time: str=None) -> None:
        try:
            await self.get_from_reddit(ctx, subreddit, sorting, time)
        except:
            await ctx.send("Something went wrong. Make sure subreddit name is spelled correctly.")
    
    async def check_filtering(self, ctx: commands.Context, filtering_type: str, filter_: str, default_filter: str, valid_filters: Iterable) -> str:
        if filter_ is None:
            filter_ = default_filter
        else:
            if filter_ not in valid_filters:
                await self.send_error(ctx, f"{filtering_type} filters", valid_filters)
        if filter_:
            return filter_

    async def check_time(self, ctx, time) -> str:
        return await self.check_filtering(ctx, "time", time, self.DEFAULT_TIME, self.TIME_FILTERS)
    
    async def check_sorting(self, ctx,  sorting: str) -> str:
        return await self.check_filtering(ctx, "sorting", sorting, self.DEFAULT_SORTING, self.SORTING_FILTERS)

    async def get_from_reddit(self, ctx: commands.Context, subreddit: str, sorting: str, time: str, post_limit: int=None, is_text: bool=False, hot: bool=False) -> None:
        post_limits = {
            self.TIME_FILTERS[0]: self.ALL_POST_LIMIT,
            self.TIME_FILTERS[1]: self.ALL_POST_LIMIT,
            self.TIME_FILTERS[2]: self.OTHER_POST_LIMIT,
            self.TIME_FILTERS[3]: 25,
            self.TIME_FILTERS[4]: 25,
        }
        
        sorting = await self.check_sorting(ctx, sorting)
        time = await self.check_time(ctx, time)
        
        if post_limit is None:
            post_limit = post_limits.get(time, 25)
        
        sub = reddit.subreddit(subreddit) # Get subreddit
        
        # Get posts. sub.hot() & sub.top() returns a generator of posts.
        if hot:
            posts = sub.hot()
        else:
            posts = sub.top(time_filter=time, limit=post_limit)
        
        # Get random post from list of posts
        post = random.choice(list(posts))
        
        # Format output
        if is_text:
            embed = None
            if post.selftext != "":
                out = post.selftext
            else:
                if post.url[-4:] in self.IMAGE_EXTENSIONS or post.url in self.IMAGE_HOSTS:
                    post = post.title + "\n" + post.url
                    out = post
                else:
                    out =  post.title
        else:
            embed = discord.Embed()
            embed.set_image(url=post.url)
            out = f"**{post.title}**"
        await ctx.send(out, embed=embed)
    
    async def send_error(self, ctx: commands.Context, item_type: str, valid_items: Iterable) -> None:
        """Sends error message to ctx.channel, then raises exception
        """
        items_str = ", ".join(valid_items)
        await ctx.send(f"Invalid {item_type}. Valid {item_type}s are:\n{items_str}.")
        raise discord.DiscordException(f"User provided invalid {item_type} argument.")  