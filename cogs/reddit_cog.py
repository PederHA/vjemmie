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
from typing import Iterable, Tuple, Optional, Union

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
    NSFW_WHITELIST = ["imgoingtohellforthis"]
    ALL_POST_LIMIT = 250
    OTHER_POST_LIMIT = 100
    IMAGE_EXTENSIONS = [".jpeg", ".jpg", ".png", ".gif"]
    IMAGE_HOSTS = ["imgur.com", "i.redd.it"]
    TIME_FILTERS = ["all", "year", "month", "week", "day"]
    SORTING_FILTERS = ["hot", "top"]
    DEFAULT_SORTING = SORTING_FILTERS[1]
    DEFAULT_TIME = TIME_FILTERS[0]
    TOP_ALL = (SORTING_FILTERS[1], TIME_FILTERS[0])
    POST_LIMITS = {
        TIME_FILTERS[0]: ALL_POST_LIMIT,
        TIME_FILTERS[1]: ALL_POST_LIMIT,
        TIME_FILTERS[2]: OTHER_POST_LIMIT,
        TIME_FILTERS[3]: 25,
        TIME_FILTERS[4]: 25,
    }

    def __init__(self, bot: commands.Bot, log_channel_id: int=None) -> None:
        super().__init__(bot, log_channel_id)
        self.subs = self.load_subs() # Load list of subs from disk
        for sub in self.subs:
            self._add_sub(sub)
        # Generators for changing reddit sorting.
        self.time_cycle = cycle(self.TIME_FILTERS) # Command: !rtime
        self.sorting_cycle = cycle(self.SORTING_FILTERS) # Command: !rsort
        # Avoid repeat reddit submissions in a single session
        self.posts = set()

    def load_subs(self) -> list:
        with open("db/subreddits.pkl", "rb") as f:
            return pickle.load(f)

    def dump_subs(self) -> None:
        with open("db/subreddits.pkl", "wb") as f:
            pickle.dump(self.subs, f)

    @commands.command(name="add_sub")
    async def add_sub(self, ctx: commands.Context, subreddit: str, aliases: str=None, is_text: bool=False) -> None:
        """Add <subreddit> [alias]
        
        Parameters
        ----------
        ctx : `commands.Context`
            Discord Context object
        subreddit : `str`
            Name of subreddit to add
        aliases : `str`, optional
            Alias(es) to add. String is split on every space,
            and each resulting string is treated as an alias.
        is_text : `bool`, optional
            Makes the underlying reddit method look for text posts 
            when looking for posts on `subreddit`. 
            (the default is False, which denotes that the
            subreddit is an image subreddit)
        """

        try:
            aliases = aliases.split(" ") if aliases else []
            new_command = RedditCommand(subreddit=subreddit, aliases=aliases, is_text=is_text)
            self._add_sub(new_command)
        except discord.DiscordException:
            for cmd in self.subs:
                if cmd.subreddit == subreddit:
                    commands_ = self._get_commands(cmd)
                    break
            else:
                raise
            s = "s" if "," in commands_ else ""
            await ctx.send(f"Subreddit **r/{subreddit}** already exists with command{s} **{commands_}**")
        else:
            self.dump_subs() # After adding sub, save list of subs to disk
            commands_ = self._get_commands(new_command)
            s = "s" if "," in commands_ else "" # Duplicate code yikes
            await ctx.send(f"Added subreddit **r/{subreddit}** with command{s} **{commands_}**")

    def _add_sub(self, subreddit_command: RedditCommand) -> None:
        """Creates a discord bot command from namedtuple `subreddit_command`.
        
        Parameters
        ----------
        subreddit_command : `RedditCommand`
            Name, aliases, is_text of subreddit to add.
        
        Raises
        ------
        `discord.DiscordException`
            Raised if subreddit is already added to bot.
        """

        subreddit, aliases, is_text, *_ = subreddit_command # *_ catches additional fields if they are added in the future, and prevents errors
        for command in self.bot.commands: # Check if subreddit is already added
            if command.name == subreddit:
                raise discord.DiscordException("Command already exists")

        # Method used as basis for subreddit command
        base_command = self._r
        # Pass partial method into asyncio.coroutine to make it a coroutine
        _cmd = asyncio.coroutine(partial(base_command, subreddit=subreddit, is_text=is_text))
        # Pass coroutine into commands.command to get a Discord command object
        cmd = commands.command(name=subreddit, aliases=aliases)(_cmd)

        # Add generated command to bot
        self.bot.add_command(cmd)
        # Add subreddit to cog's list of subreddits
        if subreddit_command not in self.subs:
            self.subs.append(subreddit_command)

    async def _r(self, ctx: commands.Context, sorting: str=None, time: str=None, *, subreddit: str=None, is_text: bool=False) -> None:
        """Method used as a base for adding custom subreddit commands"""
        await self.get_from_reddit(ctx, subreddit, sorting, time, is_text=is_text)

    @commands.command(name="remove_sub")
    @is_admin()
    async def remove_sub(self, ctx: commands.Context, subreddit: str) -> None:
        """ADMIN ONLY: Remove <subreddit>
        
        Parameters
        ----------
        ctx : `commands.Context`
            Discord Context object
        subreddit : `str`
            Name of subreddit to remove
        """
        for cmd in self.subs:
            if cmd.subreddit == subreddit:
                self.subs.remove(cmd)
                self.bot.remove_command(cmd.subreddit)
                self.dump_subs()
                commands_ = self._get_commands(cmd)
                await ctx.send(f"Removed subreddit **r/{subreddit}** with command(s) **{commands_}**")
                break
        else:
            await ctx.send(f"Could not find command for subreddit with name **{subreddit}**")

    @commands.command(name="subs", aliases=["subreddits"])
    async def list_subs(self, ctx: commands.Context) -> None:
        """Shows available subreddits
        
        Parameters
        ----------
        ctx : `commands.Context`
            Discord Context object
        """
        _out = []
        for cmd in sorted(self.subs, key=lambda cmd: cmd.subreddit):
            commands_ = self._get_commands(cmd)
            s = f"r/{cmd.subreddit.ljust(30)} Commands: {commands_}"
            _out.append(s)
        #out = "\n".join(_out)
        #embed = await self.get_embed(ctx, fields=[self.EmbedField("Subreddits", out)])
        #await ctx.send(embed=embed)
        out = await self.format_output(_out, item_type="subreddits")
        await ctx.send(out)

    @commands.command(name="rtime", aliases=["change_reddit_time", "reddit_time"])
    async def change_time_filtering(self, ctx: commands.Context, opt: str=None) -> None:
        """All/Year/Month/Week/Day
        
        Parameters
        ----------
        ctx : `commands.Context`
            [description]
        opt : `str`, optional
            Specify time filter manually or request current 
            time settings.
        """
        out_msg = None # Hacky, but w/e
        if opt:
            if opt in ["s", "status", "show"]:
                out_msg = f"Reddit time filtering is currently set to **{self.DEFAULT_TIME}**"
            else:
                try:
                    time = await self.check_time(ctx,opt)
                except:
                    raise discord.DiscordException(f"Invalid argument `{opt}`")
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
        """Toggle top/hot

        Aliases `!hot` and `!top` allow for manual selection of content filtering,
        while main command `!rsort` toggles between "hot" & "top".
        
        Parameters
        ----------
        ctx : `commands.Context`
            Discord Context object
        status : `str`, optional
            Optional user argument for displaying 
            current content sorting. 
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
            msg = f"Content sorting set to {self.DEFAULT_SORTING}"
        elif status in ["status", "show", "s"]:
            msg = f"Content sorting is currently set to {self.DEFAULT_SORTING}"
        else:
            msg = "Usage:\n`!rsort` toggles between hot/top\n`!hot` & `!top` for manual selection"
        embed = await self.get_embed(ctx, fields=[self.EmbedField("!rsort / !top / !hot", msg)], footer=False, timestamp=False, color="red")
        await ctx.send(embed=embed)

    @commands.command(name="rsettings", aliases=["reddit_settings"])
    async def reddit_settings(self, ctx: commands.Context) -> None:
        """Displays current Reddit settings
        
        Parameters
        ----------
        ctx : `commands.Context`
            Discord Context object
        """
        content_sorting = self.DEFAULT_SORTING
        time_sorting = self.DEFAULT_TIME
        out = "**Content:**".ljust(15, "\xa0") + content_sorting.capitalize()
        if not content_sorting == "hot":
            out += f"\n**Time:**".ljust(20, "\xa0") + time_sorting.capitalize()
        embed = await self.get_embed(
            ctx,
            fields=[self.EmbedField("Reddit settings", out)],
            footer=False,
            color="red",
            timestamp=False)
        await ctx.send(embed=embed)

    @commands.command(name="add_alias")
    async def change_sub_command(self, ctx: commands.Context, subreddit: str, alias: str) -> None:
        """Add alias for <subreddit>
        
        Parameters
        ----------
        ctx : `commands.Context`
            Discord Context object
        subreddit : `str`
            Name of subreddit to add alias for
        alias : `str`
            Name of alias
        """
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
        """ADMIN ONLY: Remove alias for subreddit
        
        Parameters
        ----------
        ctx : `commands.Context`
            Discord Context object
        subreddit : `str`
            Name of subreddit to remove alias from
        alias : `str`
            Name of alias to remove
        """
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
        """Get a random post from <subreddit> (<sorting>) (<time>)

        If no argument to parameter `subreddit` is passed in, the bot invokes
        the help command for the Reddit Cog instead.
        
        Parameters
        ----------
        ctx : `commands.Context`
            Discord Context object
        subreddit : `str`, optional
            Name of subreddit to fetch posts from. Defaults to None.
        sorting : `str`, optional
            Content sorting to filter posts by. Defaults to None.
        time : `str`, optional
            Time sorting to filter posts by. Defaults to None.
        """
        if not subreddit:
            cmd = self.bot.get_command("help")
            await ctx.invoke(cmd, "reddit")
        else:
            await self.get_from_reddit(ctx, subreddit, sorting, time)

    @commands.command(name="meme")
    async def random_meme(self, ctx: commands.Context, category: str=None) -> None:
        """Random meme. Optional categories: "edgy", "fried".
        
        Parameters
        ----------
        ctx : `commands.Context`
            Discord Context object
        category : `str`, optional
            Name of category of subreddits to look for memes in.
            Defaults to None.
        """

        default_subreddits = ["dankmemes", "dank_meme", "comedyheaven"]
        edgy_subs =  ["imgoingtohellforthis", "offensivememes", "edgymemes", "dark_humor"]
        fried_subs = ["deepfriedmemes", "nukedmemes"]

        if category in ["help", "categories", "?"]:
            # Posts an embed with a field for each category and their subreddits.
            default_field = self.EmbedField("Default", "r/"+"\nr/".join(default_subreddits))
            edgy_field = self.EmbedField("Edgy", "r/"+"\nr/".join(edgy_subs))
            fried_field = self.EmbedField("Deep Fried", "r/"+"\nr/".join(fried_subs))
            embed = await self.get_embed(ctx, title="Memes", fields=[default_field, edgy_field, fried_field], color="red")
            await ctx.send(embed=embed)
        else:
            if category in ["edgy", "edge"]:
                subreddits = edgy_subs
            elif category in ["fried", "deepfried", "df"]:
                subreddits = fried_subs
            else:
                subreddits = default_subreddits

            subreddit = random.choice(subreddits)
            await self.get_from_reddit(ctx, subreddit)

    async def _check_filtering(self, ctx: commands.Context, filtering_type: str, filter_: str, default_filter: str, valid_filters: Iterable) -> str:
        """Small helper method for getting a valid sorting filter
        for Praw and reducing code duplication in RedditCog.check_time()
        and RedditCog.check_sorting()

        NOTE: Yes, this is absolute trash.
        
        Parameters
        ----------
        ctx : `commands.Context`
            Discord Context object
        filtering_type : `str`
            Human readable name of sorting filter. 
        filter_ : `str`
            Reddit sorting filter. Must be in one of
            RedditCog.TIME_FILTERS or RedditCog.SORTING_FILTERS
        default_filter : `str`
            Default filter to be used if `filter_` is None.
        valid_filters : `Iterable`
            An iterable containing valid sorting filters for 
            the given `filtering_type`.
        
        Returns
        -------
        `str`
            A valid sorting filter for `filtering_type`.
        """

        if filter_ is None:
            filter_ = default_filter
        else:
            if filter_ not in valid_filters:
                raise discord.DiscordException(f"{filter_} is not a valid Reddit sorting filter.")
        if filter_:
            return filter_

    async def check_time(self, ctx, time) -> str:
        return await self._check_filtering(ctx, "time", time, self.DEFAULT_TIME, self.TIME_FILTERS)

    async def check_sorting(self, ctx,  sorting: str) -> str:
        return await self._check_filtering(ctx, "sorting", sorting, self.DEFAULT_SORTING, self.SORTING_FILTERS)

    def _is_image_content(self, url) -> bool:
        #return False if not url else "." in url and (url[-4:] in self.IMAGE_EXTENSIONS or any(img_host in url for img_host in self.IMAGE_HOSTS))
        return False if not url else any(url.endswith(end) for end in self.IMAGE_EXTENSIONS)

    def _is_nsfw(self, ctx: commands.Context, sub_or_post: Union[praw.models.Submission, praw.models.Subreddit]) -> bool:
        if isinstance(sub_or_post, praw.models.Submission):
            post = sub_or_post
            return post.over_18 and not ctx.channel.nsfw and post.subreddit.display_name.lower() not in self.NSFW_WHITELIST
        elif isinstance(sub_or_post, praw.models.Subreddit):
            sub = sub_or_post
            return sub.over18 and not ctx.channel.nsfw and sub.display_name.lower() not in self.NSFW_WHITELIST
        else:
            raise TypeError("Inappropriate argument type")




    async def _get_random_reddit_post(self, posts: list, post_limit: int) -> praw.models.Submission:
        """Attempts to get a random reddit post that has not
        yet been posted in the current bot session. 
        
        A bot session is defined as the period of time from 
        bot startup to invocation of this method.
        
        Parameters
        ----------
        posts : `set`
            A `praw` Reddit submission generator
        post_limit : int
            Number of attempts to look for a unique post before
            raising exception and exiting.
        
        Raises
        ------
        `discord.DiscordException`
            Raised if a unique Reddit post can not be found.
        
        Returns
        -------
        `praw.models.Submission`
            A Reddit post unique to the current bot session.
        """

        n = 0
        post = None
        # Get random post
        while post in self.posts or post is None: # TODO for Python3.8: Assignment operator
            post = random.choice(list(posts))
            if post in self.posts:
                n += 1
                posts.remove(post)
            else:
                return post
            if n >= post_limit:
                raise discord.DiscordException("Could not find unique reddit post")

    async def get_reddit_post(self, subreddit: str, posts: list, post_limit: int, is_text: bool) -> Tuple[str, Optional[str]]:
        """Attempts to get a Reddit post unique to the current bot session.
        
        Subsequently formats the post according to its attributes and whether
        or not the given param:`subreddit` is a text-only subreddit as denoted by 
        param:`is_text`.
        
        Parameters
        ----------
        subreddit : `str`
            Name of subreddit
        posts : `list`
            List of Reddit posts
        post_limit : `int`
            Number of posts to retrieve
        is_text : bool
            Whether or not the subreddit is a text subreddit.
            If True, prioritizes posting post title and self-text
            over an image URL.
        
        Raises
        ------
        `discord.DiscordException`
            Raised if no image posts can be found that match the given
            criterias.
        
        Returns
        -------
        `Tuple[str, Optional[str]]`
            A tuple containing a post title or self-text and an optional
            image url. In case of a "self" submission this will be None.
        """

        post = await self._get_random_reddit_post(posts, post_limit)
        image_url = None
        # Prioritize selftext for text subreddits
        if is_text:
            # 1st Prio: Post selftext / title.
            if post.selftext:
                if len(post.selftext) > len(post.title):
                    _out = post.selftext
                else:
                    _out = post.title
            # 2nd prio: post.title + embedded image if post url is an image
            else:
                _out = post.title
                if self._is_image_content(post.url):
                    image_url = post.url
        # Only post images for image subreddits
        else:
            n = 0
            limit = len(posts)
            # Get new post if random post does not contain an image URL
            while not self._is_image_content(post.url):
                post = await self._get_random_reddit_post(posts, post_limit)
                n += 1
                if n >= limit:
                    raise discord.DiscordException("Could not find an image submission.")
            _out = f"r/{subreddit}: {post.title}"
            image_url = post.url
        self.posts.add(post)
        return _out, image_url

    async def _get_subreddit_posts(self, ctx, subreddit: str, sorting: str=None, time: str=None, post_limit: int=None) -> set:
        # Get subreddit
        sub = reddit.subreddit(subreddit)

        # Check if NSFW subreddit
        if self._is_nsfw(ctx, sub):
            #if sub.over18 and not ctx.channel.nsfw and subreddit.lower() not in self.NSFW_WHITELIST:
            raise discord.DiscordException("Cannot post NSFW content in a non-NSFW channel!")

        # Get posts generator
        if sorting == "hot":
            posts = sub.hot()
        else:
            posts = sub.top(time_filter=time, limit=post_limit)
        return set(posts)

    async def get_from_reddit(self,
                              ctx: commands.Context,
                              subreddit: str,
                              sorting: str = None,
                              time: str = None,
                              post_limit: int = None,
                              is_text: bool = False,
                              allow_nsfw: bool = False) -> None:
        # Parse arguments to params sorting & time
        sorting = await self.check_sorting(ctx, sorting) # "top"/"hot"
        time = await self.check_time(ctx, time) # "all", "year", "month", "week", "day"

        # Get post limit
        if post_limit is None:
            post_limit = self.POST_LIMITS.get(time, 25)

        # Get list of Reddit posts from a given subreddit
        posts = await self._get_subreddit_posts(ctx, subreddit, sorting, time, post_limit)

        # Select a random post from list of posts
        out_text, image_url = await self.get_reddit_post(subreddit, posts, post_limit, is_text)

        # Rehost image to discord CDN if image is hosted on imgur
        if image_url and "imgur" in image_url:
            msg = await self.upload_image_to_discord(image_url)
            image_url = msg.attachments[0].url

        # Embed image if selected post has an associated image URL
        if image_url:
            embed = await self.get_embed(ctx, title=out_text, image_url=image_url, color="red")
            await ctx.send(embed=embed)

        # Send plain text otherwise
        else:
            # Break up text posts into 1800 char long chunks
            LIMIT = 1800
            chunks = [out_text[i:i+LIMIT] for i in range(0, len(out_text), LIMIT)]
            for chunk in chunks:
                await ctx.send(chunk)

    def _get_commands(self, cmd: RedditCommand) -> str:
        """
        Generates string of commands associated with a RedditCommand instance.
        Should only be used to generate string of commands for existing subreddits,
        when, for example, iterating over `RedditCog.subs`.
        
        Returns:
            str: Commands prefixed with the bot's command prefix, separated by commas
        
        Example:
            >>> _get_commands(RedditCommand(subreddit="dota2", aliases=["d2", "dota"]))
            '!d2, !dota, !dota2'
        """
        subreddit, aliases, *_ = cmd
        command = self.bot.command_prefix
        return command + f", {command}".join(aliases+[subreddit]) if aliases else command + subreddit

    async def _send_error(self, ctx: commands.Context, item_type: str, valid_items: Iterable) -> None:
        """Sends error message to ctx.channel, then raises exception
        """
        items_str = ", ".join(valid_items)
        await ctx.send(f"Invalid {item_type}. Valid {item_type}s are:\n{items_str}.")
        raise discord.DiscordException(f"User provided invalid {item_type} argument.")
