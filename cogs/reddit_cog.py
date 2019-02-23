import asyncio
import datetime
import math
import pickle
import random
import re
import secrets
import traceback
from collections import namedtuple
from functools import partial, partialmethod
from itertools import cycle
from typing import Iterable, Tuple

import discord
import praw
from discord.ext import commands

from cogs.admin_utils import is_admin, is_not_blacklisted
from cogs.base_cog import BaseCog
from ext_module import ExtModule

reddit = praw.Reddit(
    client_id=secrets.REDDIT_ID,
    client_secret=secrets.REDDIT_SECRET,
    user_agent=secrets.REDDIT_USER_AGENT,
)

RedditCommand = namedtuple("RedditCommand", ["subreddit", "aliases", "is_text"], defaults=[[], False])

class RedditCog(BaseCog):
    ALL_POST_LIMIT = 250
    OTHER_POST_LIMIT = 100
    IMAGE_EXTENSIONS = [".jpg", ".png", ".gif"]
    IMAGE_HOSTS = ["imgur.com", "i.redd.it"]
    TIME_FILTERS = ["all", "year", "month", "week", "day"]
    SORTING_FILTERS = ["hot", "top"]
    DEFAULT_SORTING = SORTING_FILTERS[1]
    DEFAULT_TIME = TIME_FILTERS[0]
    TOP_ALL = (SORTING_FILTERS[1], TIME_FILTERS[0])

    def __init__(self, bot: commands.Bot, log_channel_id: int=None) -> None:
        super().__init__(bot, log_channel_id)
        self.subs = self.load_subs() # Load list of subs from disk
        for sub in self.subs:
            self._add_sub(sub)
        # Generators for changing reddit sorting.
        self.time_cycle = cycle(self.TIME_FILTERS) # Command: !rtime
        self.sorting_cycle = cycle(self.SORTING_FILTERS) # Command: !rsort

    def load_subs(self) -> list:
        with open("db/subreddits.pkl", "rb") as f:
            return pickle.load(f)
    
    def dump_subs(self) -> None:
        with open("db/subreddits.pkl", "wb") as f:
            pickle.dump(self.subs, f)

    @commands.command(name="add_sub", aliases=["add_r", "addr", "newr", "nr"])
    async def add_sub(self, ctx: commands.Context, subreddit: str, aliases: str=None, is_text: bool=False) -> None:
        try:
            aliases = aliases.split(" ") if aliases else []
            new_command = RedditCommand(subreddit=subreddit, aliases=aliases, is_text=is_text)
            self._add_sub(new_command)
        except discord.DiscordException:
            for cmd in self.subs:
                if cmd.subreddit == subreddit:
                    commands_ = self.get_commands(cmd)
                    break
            else:
                raise
            s = "s" if "," in commands_ else ""
            await ctx.send(f"Subreddit **r/{subreddit}** already exists with command{s} **{commands_}**")
        else:
            self.dump_subs() # After adding sub, save list of subs to disk
            commands_ = self.get_commands(new_command)
            s = "s" if "," in commands_ else "" # Duplicate code yikes
            await ctx.send(f"Added subreddit **r/{subreddit}** with command{s} **{commands_}**")
    
    def _add_sub(self, subreddit_command: RedditCommand) -> None:
        subreddit, aliases, is_text, *_ = subreddit_command # *_ catches additional fields if they are added in the future, and prevents errors
        for command in self.bot.commands: # Check if subreddit is already added
            if command.name == subreddit:
                raise discord.DiscordException("Command already exists")
        base_command = self._r # The method that is used to create custom subreddit commands
        _cmd = asyncio.coroutine(partial(base_command, subreddit=subreddit, is_text=is_text))
        cmd = commands.command(name=subreddit, aliases=aliases)(_cmd) # Use partial coroutine to create command object
        self.bot.add_command(cmd) # Add generated command to bot
        if subreddit_command not in self.subs:
            self.subs.append(subreddit_command) # Add subreddit to cog's list of subreddits
    
    async def _r(self, ctx: commands.Context, sorting: str=None, time: str=None, *, subreddit: str=None, is_text: bool=False) -> None:
        await self.get_from_reddit(ctx, subreddit, sorting, time, is_text=is_text)
    
    @commands.command(name="remove_sub")
    @is_admin()
    async def remove_sub(self, ctx: commands.Context, subreddit: str) -> None:
        for cmd in self.subs:
            if cmd.subreddit == subreddit:
                self.subs.remove(cmd)
                self.bot.remove_command(cmd.subreddit)
                self.dump_subs()
                commands_ = self.get_commands(cmd)
                await ctx.send(f"Removed subreddit **r/{subreddit}** with command(s) **{commands_}**")
                break
        else:
            await ctx.send(f"Could not find command for subreddit with name **{subreddit}**")
  
    def get_commands(self, cmd: RedditCommand) -> str:
        """
        Generates string of commands associated with a RedditCommand instance.
        Should only be used to generate string of commands for existing subreddits,
        when, for example, iterating over `RedditCog.subs`.
        
        Returns:
            str: Commands prefixed with the bot's command prefix, separated by commas
        
        Example:
            >>> get_commands(RedditCommand(subreddit="dota2", aliases=["d2", "dota"]))
            '!d2, !dota, !dota2'
        """
        subreddit, aliases, *_ = cmd
        command = self.bot.command_prefix
        return command + f", {command}".join(aliases+[subreddit]) if aliases else command + subreddit
    
    @commands.command(name="subs", aliases=["subreddits"])
    async def list_subs(self, ctx: commands.Context) -> None:
        _out = []
        for cmd in self.subs:
            commands_ = self.get_commands(cmd)
            s = f"r/{cmd.subreddit.ljust(30)} Command(s): {commands_}"
            _out.append(s)
        out = await self.format_output(_out, item_type="subreddits")
        await ctx.send(out)

    @commands.command(name="change_reddit_time", aliases=["rtime", "reddit_time"])
    async def change_time_filtering(self, ctx: commands.Context, opt: str=None) -> None:
        out_msg = None # Hacky, but w/e
        if opt:
            if opt in ["s", "status", "show"]:
                out_msg = f"Reddit time filtering is currently set to **{self.DEFAULT_TIME}**"
            else:
                try:
                    time = await self.check_time(ctx,opt)
                except:
                    await ctx.send(f"Invalid argument {time}")
                else:
                    # Match up time filter cycle and current time
                    _next_time = next(self.time_cycle)
                    while time != _next_time:
                        _next_time = next(self.time_cycle)
        else:
            time = next(self.time_cycle) # Pump generator if no opt argument
        if not out_msg:
            self.DEFAULT_TIME = time
            out_msg = f"Reddit time filtering set to **{time}**."
        await ctx.send(out_msg)
    
    @commands.command(name="rsort", aliases=["hot", "top"])
    async def change_content_sorting(self, ctx: commands.Context, status: str=None) -> None:
        """
        Toggles between "hot" and "top" content filtering on Reddit.

        ----
        
        Aliases `hot` and `top` allow for manual selection of content filtering, while
        main command `rsort` toggles between "hot" & "top".
        
        Args:
            status (str, optional): Defaults to None. Optional user argument for 
            displaying current content sorting. 

        """
        if not status:
            if ctx.invoked_with == "hot":
                self.DEFAULT_SORTING = await self.check_sorting(ctx, "hot") # Too complicated? Prevents errors, though
            elif ctx.invoked_with == "top":
                self.DEFAULT_SORTING = await self.check_sorting(ctx, "top")
            else:
                sort = next(self.sorting_cycle)
                if sort == self.DEFAULT_SORTING: # Avoid setting same value as current if !top or !hot has been used
                    sort = next(self.sorting_cycle)
                self.DEFAULT_SORTING = sort
            msg = f"Reddit content sorting set to {self.DEFAULT_SORTING}"
        elif status in ["status", "show", "s"]:
            msg = f"Reddit content sorting is currently set to {self.DEFAULT_SORTING}"
        else:
            msg = "Usage:\n\n+ !rsort switches between hot/top\n+ !hot & !top for manual selection"
        await ctx.send(await self.make_codeblock(msg, "diff"))

    @commands.command(name="reddit_settings", aliases=["rsettings"])
    async def reddit_settings(self, ctx: commands.Context) -> None:
        content_sorting = self.DEFAULT_SORTING
        time_sorting = self.DEFAULT_TIME
        out = "Content: ".ljust(10) + content_sorting
        if not content_sorting == "hot":
            out += f"\nTime:".ljust(10) + time_sorting
        out = await self.make_codeblock("Reddit settings:\n\n"+out)
        await ctx.send(out)
    
    @commands.command(name="add_alias")
    async def change_sub_command(self, ctx: commands.Context, subreddit: str, alias: str) -> None:
        if not alias.isnumeric():
            alias = alias.lower()
            for idx, subreddit_cmd in enumerate(self.subs):
                if subreddit == subreddit_cmd.subreddit:
                    self.subs.pop(idx)
                    subreddit_cmd.aliases.append(alias)
                    self.subs.append(subreddit_cmd)
                    self.dump_subs()
                    await ctx.send(f"Added alias **!{alias}** for subreddit **r/{subreddit}**")
                    #await ctx.send(f"Command for subreddit **r/{subreddit}** changed to **!{command}**.\n"
                    #                "Changes take effect on next restart.")
                    break
        else:
            await ctx.send("Invalid alias name. Can only contain letters a-z.")
    
    @commands.command(name="remove_alias")
    @is_admin()
    async def remove_alias(self, ctx: commands.Context, subreddit: str, alias: str) -> None:
        for idx, subreddit_cmd in enumerate(self.subs):
            if subreddit == subreddit_cmd.subreddit:
                try:
                    subreddit_cmd.aliases.remove(alias)
                except:
                    await ctx.send(f"No such alias **!{alias}** for subreddit **r/{subreddit}**")
                else:
                    self.subs.pop(idx)
                    self.subs.append(subreddit_cmd)
                    self.dump_subs()
                    await ctx.send(f"Removed alias **!{alias}** for subreddit **r/{subreddit}**")
                break        

    @commands.command(name="reddit")
    async def reddit(self, ctx: commands.Context, subreddit: str=None, sorting: str=None, time: str=None) -> None:
        if not subreddit:
            reddit_commands = self.bot.get_command("rcommands")
            await ctx.invoke(reddit_commands)
        else:
            await self.get_from_reddit(ctx, subreddit, sorting, time)
    
    async def _check_filtering(self, ctx: commands.Context, filtering_type: str, filter_: str, default_filter: str, valid_filters: Iterable) -> str:
        if filter_ is None:
            filter_ = default_filter
        else:
            if filter_ not in valid_filters:
                await self._send_error(ctx, f"{filtering_type} filters", valid_filters) # Sends message and raises exception
        if filter_:
            return filter_

    async def check_time(self, ctx, time) -> str:
        return await self._check_filtering(ctx, "time", time, self.DEFAULT_TIME, self.TIME_FILTERS)
    
    async def check_sorting(self, ctx,  sorting: str) -> str:
        return await self._check_filtering(ctx, "sorting", sorting, self.DEFAULT_SORTING, self.SORTING_FILTERS)

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
        
        # Get posts generator
        if hot:
            posts = sub.hot()
        else:
            posts = sub.top(time_filter=time, limit=post_limit)
        
        # Get random post from list of posts
        try:
            post = random.choice(list(posts))
        except BaseException as e:
            # TODO: Add responses for different status codes
            await ctx.send(
                f"Could not retrieve posts from reddit. Error: {', '.join(e.args)}\n"
                "Make sure subreddit name is spelled correctly or try again later."
                )
            await self.send_log(str(e), ctx)
       
        # Generate message that bot will post
        #####################################
        def is_image_content(url) -> bool:
            return url[-4:] in self.IMAGE_EXTENSIONS or any(img_host in url for img_host in self.IMAGE_HOSTS)
        # NOTE: Could reduce code duplication here but cba rn
        embed_content = None
        md_style = ""
        opts = {}
        # Prioritize selftext for text subreddits
        if is_text:
            # 1st Prio: Post selftext / title. 
            if post.selftext:
                # Emojipasta, copypasta, etc. submissions sometimes put the
                # joke/content in the title
                if len(post.selftext) > len(post.title):
                    _out = post.selftext
                else:
                    _out = post.title
            # 2nd prio: post.title + embedded image if post url is an image
            else:
                _out = post.title
                if is_image_content(post.url):
                    embed_content = post.url
        # Prioritize image for image subreddits
        else:
            # 1st prio: Post title + embedded image
            if is_image_content(post.url):
                _out = post.title
                embed_content = post.url
            # 2nd prio: Post title + post selftext
            elif post.selftext:
                _out = f"**{post.title}**\n{post.selftext}"
            # 3rd Prio: Post title + post URL
            else:
                _out = f"**{post.title}**\n{post.url}"
        
        # Deal with text posts whose size exceeds Discord's max message length
        LIMIT = 1800
        n_chunks = math.ceil(len(_out)/LIMIT)  
        if n_chunks > 1:    # split into chunks if text output exceeds 1800 chars
            _temp = ""
            chunks = []
            for char in _out: # TODO: Change to enumerate(_out), check every 100 chars
                if len(_temp) < LIMIT:
                    _temp += char # This is probably very inefficient due to the use of += for every char
                else:
                    chunks.append(_temp)
                    _temp = char
            else:
                chunks.append(_temp) 
            for chunk in chunks:
                await ctx.send(chunk)
        else:
            if embed_content:
                md_style = "**"
                embed = discord.Embed()
                embed.set_image(url=embed_content)
                opts = {"embed": embed}
            out = f"{md_style}{_out}{md_style}"
            await ctx.send(out, **opts)
             
    @commands.command(name="redditcommands", aliases=["rcommands", "reddit_commands"])
    async def reddit_commands(self, ctx: commands.Context) -> None:
        _out = [
            cmd for cmd in self.bot.commands
            if cmd.cog_name == self.__class__.__name__
        ]
        await ctx.send(await self.format_output(_out, item_type="Reddit commands"))
    
    async def _send_error(self, ctx: commands.Context, item_type: str, valid_items: Iterable) -> None:
        """Sends error message to ctx.channel, then raises exception
        """
        items_str = ", ".join(valid_items)
        await ctx.send(f"Invalid {item_type}. Valid {item_type}s are:\n{items_str}.")
        raise discord.DiscordException(f"User provided invalid {item_type} argument.")
