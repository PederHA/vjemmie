import asyncio
import datetime
import json
import math
import os
import pickle
import random
import re
import traceback
from collections import defaultdict, namedtuple
from functools import partial, partialmethod
from itertools import cycle
from pathlib import Path
from typing import Iterable, Optional, Tuple, Union, Dict, List

import discord
import praw
from discord.ext import commands, tasks
from prawcore.exceptions import Forbidden, NotFound, Redirect
from praw.models import Submission
from recordclass import recordclass

from ..utils.caching import get_cached
from ..utils.checks import admins_only
from ..utils.commands import add_command
from ..utils.converters import BoolConverter
from ..utils.exceptions import CommandError
from ..utils.json import dump_json
from ..utils.parsing import is_valid_command_name
from .base_cog import BaseCog, EmbedField

reddit: praw.Reddit = None # Initialized by RedditCog

RedditCommand = namedtuple("RedditCommand", ["subreddit", "aliases", "is_text"], defaults=[[], False])


async def _reddit_command_base(obj: commands.Cog, ctx: commands.Context, sorting: str=None, time: str=None, *, subreddit: str=None, is_text: bool=False) -> None:
    """Method used as a base for adding custom subreddit commands."""
    await obj.get_from_reddit(ctx, subreddit, sorting, time, is_text=is_text)


class RedditSubmissions:
    """Caches Reddit submissions for all guilds."""

    _submissions: Dict[str, List[Submission]] = {}

    def get(self, guild_id: int, subreddit: str, sorting: str, time: str) -> List[Submission]:
        """Retrieves a list of Reddit Submissions."""
        k = self._get_key(guild_id, subreddit, sorting, time)
        return self._submissions.get(k, [])

    def add(self, submissions: List[Submission], guild_id: int, subreddit: str, sorting: str, time: str) -> None:
        k = self._get_key(guild_id, subreddit, sorting, time)
        self._submissions[k] = submissions

    def clear(self) -> None:
        """Clears all submissions for all guilds."""
        self._submissions.clear()

    def _get_key(self, guild_id: int, subreddit: str, sorting: str, time: str) -> str:
        return f"{guild_id}{subreddit}{sorting}{time}"


class RedditCog(BaseCog):
    """Reddit commands."""

    EMOJI = "<:leddit:565523334276841498>"
    
    DIRS = [
        "db/reddit"
    ]
    FILES = [
        "db/reddit/subs.json",
        "db/reddit/nsfw_whitelist.json"
    ]

    COG_COLOR = "red"

    ALL_POST_LIMIT = 250
    OTHER_POST_LIMIT = 100
    
    IMAGE_HOSTS = ["imgur.com", "i.redd.it"]
    TIME_FILTERS = ["all", "year", "month", "week", "day"]
    SORTING_FILTERS = ["hot", "top"]
    DEFAULT_SORTING = SORTING_FILTERS[1]
    DEFAULT_TIME = TIME_FILTERS[0]
    TOP_ALL = (SORTING_FILTERS[1], TIME_FILTERS[0])
    POST_LIMITS = {
        "all": ALL_POST_LIMIT,
        "year": ALL_POST_LIMIT,
        "month": OTHER_POST_LIMIT,
        "week": 25,
        "day": 25,
    }

    submissions = RedditSubmissions()

    def __init__(self, bot: commands.Bot) -> None:
        super().__init__(bot)

        # Load subreddits
        self.subs = self.load_subs()
        for sub in self.subs.values():
            self._add_sub(sub)
        
        # Iterators for changing reddit sorting.
        self.time_cycle = cycle(self.TIME_FILTERS) # Command: !rtime
        self.sorting_cycle = cycle(self.SORTING_FILTERS) # Command: !rsort
        
        # Initiate loop that clears reddit submission cache daily
        self.submission_refresh_loop.start()
    
    @property
    def NSFW_WHITELIST(self):
        return get_cached("db/reddit/nsfw_whitelist.json", category="reddit")
    
    @tasks.loop(seconds=86400.0)
    async def submission_refresh_loop(self) -> None:
        """Wipes reddit submission cache once daily"""
        self.submissions.clear()    
    
    def cog_unload(self) -> None:
        self.submission_refresh_loop.cancel()        

    def load_subs(self) -> dict:
        subs = get_cached("db/reddit/subs.json")
        return {subreddit: RedditCommand(sub[0], sub[1], sub[2]) for subreddit, sub in subs.items()} if subs else {}

    async def dump_subs(self) -> None:
        if not self.subs:
            return
        await dump_json("db/reddit/subs.json", self.subs)
    
    def _add_sub(self, subreddit_command: RedditCommand) -> None:
        """Creates a bot command from a `RedditCommand` object and adds it
        to the bot's commands.
        """
        # *_ catches additional fields if they are added in the future, and prevents errors
        subreddit, aliases, is_text, *_ = subreddit_command
        add_command(self, 
                    _reddit_command_base,
                    name=subreddit,
                    aliases=aliases,
                    help=f"Gets a random post from r/{subreddit}",
                    hidden=True,
                    subreddit=subreddit,
                    is_text=is_text
                   )
    
    @commands.group(name="reddit", usage="<subcommand>")
    async def reddit(self, ctx: commands.Context, opt: str=None, *args) -> None:
        """Reddit commands
        """
        # Try to get subcommand
        cmd = self.bot.get_command(f"reddit {opt}")
        if not cmd:
            if opt:
                await ctx.send(
                    f'**"{opt}"** is not a valid argument for **`{self.bot.command_prefix}reddit`**'
                    )
            else:
                await ctx.send(f"No argument provided!")
            await ctx.invoke(self.bot.get_command("help"), "reddit")
        else:
            await ctx.invoke(cmd, *args)
    
    @reddit.command(name="get", aliases=["sub"])
    async def reddit_get_sub_post(self, ctx: commands.Context, subreddit: str, time: str=None, sorting: str=None) -> None:
        """Get a random post from <subreddit>"""
        await self.get_from_reddit(ctx, subreddit, sorting, time)
    
    @reddit.command(name="add", aliases=["add_sub"])
    async def add_sub(self, ctx: commands.Context, subreddit: str, aliases: str=None, is_text: BoolConverter(["text"])=False) -> None:
        """Add <subreddit> [alias]
        
        Parameters
        ----------
        ctx : `commands.Context`
            Discord Context object
        subreddit : `str`
            Name of subreddit to add
        aliases : `str`, optional
            String of aliases separated by spaces.
        is_text : `bool`, optional
            Denotes that subreddit contains primarily text posts.
            (the default is False, which denotes that the
            subreddit is an image subreddit)
        """

        try:
            al = aliases.split(" ") if aliases else []
            if not is_valid_command_name(subreddit) or not all(is_valid_command_name(a) for a in al):
                raise CommandError("Command name can only include letters a-z and numbers 0-9.")
            new_command = RedditCommand(subreddit=subreddit, aliases=al, is_text=is_text)
            self._add_sub(new_command)
        except discord.DiscordException:
            cmd = self.subs.get(subreddit)
            if not cmd:
                raise
            commands_ = self._get_commands(cmd)
            s = "s" if "," in commands_ else ""
            raise CommandError(f"Subreddit **r/{subreddit}** already exists with command{s} **{commands_}**")
        else:
            self.subs[subreddit] = new_command
            await self.dump_subs() # After adding sub, save list of subs to disk
            commands_ = self._get_commands(new_command)
            s = "s" if "," in commands_ else "" # Duplicate code yikes
            await ctx.send(f"Added subreddit **r/{subreddit}** with command{s} **{commands_}**")

    @reddit.command(name="remove", aliases=["remove_sub"])
    @admins_only()
    async def remove_sub(self, ctx: commands.Context, subreddit: str) -> None:
        """Remove <subreddit>
        
        Parameters
        ----------
        ctx : `commands.Context`
            Discord Context object
        subreddit : `str`
            Name of subreddit to remove
        """
        cmd = self.subs.get(subreddit)
        # Check if subreddit command exists
        if not cmd:
            raise CommandError(f"Could not find command for subreddit with name **{subreddit}**")
        
        # Remove sub from instance subreddit dict
        self.subs.pop(subreddit)
        # Remove associated command
        self.bot.remove_command(cmd.subreddit)
        # Save changes
        await self.dump_subs()
        # Get commands associated with removed subreddit
        commands_ = self._get_commands(cmd)
        await ctx.send(f"Removed subreddit **r/{subreddit}** with command(s) **{commands_}**")

    @reddit.command(name="subs", aliases=["list", "subreddits"])
    async def list_subs(self, ctx: commands.Context) -> None:
        """Shows available subreddits
        
        Parameters
        ----------
        ctx : `commands.Context`
            Discord Context object
        """
        if not self.subs:
            raise CommandError("No subreddits are added!")
        
        _out = []
        longest_subreddit = max([len(cmd.subreddit) for cmd in self.subs.values()]) + 1
        for cmd in sorted(self.subs.values(), key=lambda cmd: cmd.subreddit):
            commands_ = self._get_commands(cmd)
            s = f"`r/{cmd.subreddit.ljust(longest_subreddit, self.EMBED_FILL_CHAR)}:`\xa0`{commands_}`"
            _out.append(s)  
        out = "\n".join(_out)
        # TODO: Find a non-retarded way to align Commands text with commands column
        await self.send_embed_message(ctx, f"Subreddit{' '*round(longest_subreddit*1.7)}Commands", out, limit=1000)

    @reddit.command(name="time")
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
                    time = await self.check_time(ctx, opt)
                except:
                    raise CommandError(f"Invalid argument `{opt}`")
                else:
                    # Match up time filter cycle and current time
                    _next_time = next(self.time_cycle)
                    while time != _next_time:
                        _next_time = next(self.time_cycle)
        else:
            time = next(self.time_cycle) # Pump generator if no opt argument
            if time == self.DEFAULT_TIME:
                time = next(self.time_cycle)
        if not out_msg:
            self.DEFAULT_TIME = time
            out_msg = f"Reddit time filtering set to **{time}**."
        await ctx.send(out_msg)

    @reddit.command(name="sort", aliases=["sorting"])
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
            msg = f"Content sorting set to **`{self.DEFAULT_SORTING}`**"
        elif status in ["status", "show", "s"]:
            msg = f"Content: **`{self.DEFAULT_SORTING}`**"
        else:
            msg = "Usage:\n`!rsort` toggles between hot/top\n`!hot` & `!top` for manual selection"
        
        await self.send_embed_message(ctx, 
                                      title="Reddit", 
                                      description=msg, 
                                      footer=False, 
                                      timestamp=False, 
                                      color=self.COG_COLOR)

    @reddit.command(name="settings")
    async def reddit_settings(self, ctx: commands.Context) -> None:
        """Displays current Reddit settings
        
        Parameters
        ----------
        ctx : `commands.Context`
            Discord Context object
        """
        content_sorting = self.DEFAULT_SORTING
        time_sorting = self.DEFAULT_TIME
        
        # Display content filtering
        out = "Content:".ljust(15, "\xa0") + f"**`{content_sorting.capitalize()}`**"
        
        # Display time filtering if "hot" is not active
        if not content_sorting == "hot":
            out += f"\nTime:".ljust(20, "\xa0") + f"**`{time_sorting.capitalize()}`**"
        
        await self.send_embed_message(
            ctx,
            title="Reddit settings",
            description=out,
            color=self.COG_COLOR,
            timestamp=False)

    @reddit.command(name="alias", aliases=["add_alias"])
    async def add_subreddit_alias(self, ctx: commands.Context, subreddit: str, alias: str) -> None:
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
        alias = alias.lower()
        subreddit = subreddit.lower()

        # Only accept aliases with letters a-z
        if not is_valid_command_name(alias):
            raise CommandError("Invalid alias name. Can only contain letters a-z.")
        
        # Check if subreddit exists as a bot command
        if not subreddit in self.subs:
            raise CommandError(f"Subreddit {subreddit} is not added as a bot command!")

        # Add new alias
        self.subs[subreddit].aliases.append(alias)
        # Save changes & reload subreddit commands
        await self.dump_subs()
        await self._reload_sub_commands()
        await ctx.send(f"Added alias **!{alias}** for subreddit **r/{subreddit}**")
    
    async def _reload_sub_commands(self):
        """Reloads all subreddit commands.
        """
        # Need some sort of dict / set data type here for fast hash table lookups
        
        # Get bot subreddits
        subs = self.load_subs()
        # Get all bot commands
        commands = self.bot.commands

        for subreddit, sub_values in subs.items():
            for cmd in commands:
                if subreddit == cmd.name:
                    self.bot.remove_command(cmd.name)
                    self._add_sub(sub_values) 
                    break

    @reddit.command(name="remove_alias")
    @admins_only()
    async def remove_alias(self, ctx: commands.Context, subreddit: str, alias: str) -> None:
        """Remove alias for subreddit
        
        Parameters
        ----------
        ctx : `commands.Context`
            Discord Context object
        subreddit : `str`
            Name of subreddit to remove alias from
        alias : `str`
            Name of alias to remove
        """
        subreddit = subreddit.lower()
        alias = alias.lower()

        if subreddit not in self.subs:
            raise CommandError(f"Subreddit {subreddit} is not added as a bot command!")
        
        if alias not in self.subs[subreddit].aliases:
            raise CommandError(f"No such alias **!{alias}** for subreddit **r/{subreddit}**")
        
        self.subs[subreddit].aliases.remove(alias)
        await self.dump_subs()
        await self._reload_sub_commands()
        await ctx.send(f"Removed alias **!{alias}** for subreddit **r/{subreddit}**")

    @commands.command(name="meme", usage="<url> or 'help'")
    async def meme(self, ctx: commands.Context, category: str="default") -> None:
        """Random meme. Optional categories: "edgy", "fried"."""
        subs = {
            "default": ["dankmemes", "dank_meme", "comedyheaven"],
            "edgy": ["imgoingtohellforthis", "dark_humor", "darkhumorandmemes"],
            "fried": ["deepfriedmemes", "nukedmemes"]
        }

        category = category.casefold()

        # Post an embed with a field for each category and their respective subreddits.
        if category in ["help", "categories", "?"]:
            s = []
            for category, _subs in subs.items():
                s.append(EmbedField(f"`{category}`", "r/"+"\nr/".join(_subs)))
            embed = await self.get_embed(ctx, title="Memes", fields=s, color=self.COG_COLOR)
            return await ctx.send(embed=embed)

        # Get list of subreddits for given category
        subreddits = subs.get(category)
        if not subreddits:
            raise CommandError(f"Category `{category}` does not exist. "
            f"Type `{self.bot.command_prefix}{ctx.invoked_with}` to see available categories.")
        
        # Get random subreddit from list of subreddits
        subreddit = random.choice(subreddits)

        await self.get_from_reddit(ctx, subreddit)
    
    @reddit.command(name="wipe", aliases=["clear"])
    @admins_only()
    async def wipe_reddit_cache(self, ctx: commands.Context) -> None:
        self.init_submissions_cache()
        await ctx.send("Wiped Reddit submissions cache successfully!")

    async def _check_filtering(self, filtering_type: str, filter_: Optional[str], default_filter: str, valid_filters: Iterable) -> str:
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
        filter_ : `Optional[str]`
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
        if filter_ and filter_ not in valid_filters:
            raise CommandError(f"{filter_} is not a valid Reddit sorting filter.")
        
        return filter_ or default_filter
    
    async def check_time(self, ctx, time: Optional[str]) -> str:
        return await self._check_filtering("time", time, self.DEFAULT_TIME, self.TIME_FILTERS)

    async def check_sorting(self, ctx,  sorting: Optional[str]) -> str:
        return await self._check_filtering("sorting", sorting, self.DEFAULT_SORTING, self.SORTING_FILTERS)

    def _is_image_content(self, url: str) -> bool:
        return False if not url else any(url.endswith(end) for end in self.IMAGE_EXTENSIONS)

    def _can_send_sub_or_post(self, ctx: commands.Context, sub: Union[praw.models.Submission, praw.models.Subreddit]) -> bool:
        """Determines if subreddit or reddit submission is appropriate for a channel."""
        # Always allow if channel is marked NSFW
        if ctx.channel.nsfw:
            return True
        
        if isinstance(sub, praw.models.Submission):
            subreddit = sub.subreddit.display_name.lower()
            over_18 = sub.over_18
        elif isinstance(sub, praw.models.Subreddit):
            subreddit = sub.display_name.lower()
            over_18 = sub.over18
        else:
            raise TypeError("Argument 'sub' must be a praw Submission or Subreddit")

        return not over_18 or subreddit in self.NSFW_WHITELIST

    async def _get_random_reddit_post(self, posts: List[Submission], is_text: bool) -> Optional[Submission]:
        """Attempts to select a random reddit post that has not
        yet been posted in the current bot session from list of posts.
        """
        while True:
            if not posts:
                return None

            # Pop a random submission from the list
            post = posts.pop(random.randint(0, len(posts)-1)) 

            if is_text and not self._is_image_content(post.url) and not post.media:
                return post
            elif post.media:
                if post.media.get("reddit_video"):
                    return post
            elif not is_text and self._is_image_content(post.url):
                return post

    async def _format_reddit_post(self, post: praw.models.Submission, subreddit: str, is_text: bool) -> Tuple[str, Optional[str]]:
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
            _out = f"r/{subreddit}: {post.title}"
            image_url = post.url
        
        # Add post to cog instance's posts
        return _out, image_url

    def _get_subreddit_posts(self,
                             ctx,
                             subreddit: str,
                             sorting: str = None,
                             time: str = None,
                             post_limit: int = None,
                             allow_nsfw: bool = False
                            ) -> List[Submission]:
        # Get subreddit
        sub = reddit.subreddit(subreddit)

        # Check if NSFW subreddit
        if not self._can_send_sub_or_post(ctx, sub):
            raise CommandError("Cannot post NSFW content in a non-NSFW channel!")

        # Get posts generator
        if sorting == "hot":
            posts = sub.hot()
        else:
            posts = sub.top(time_filter=time, limit=post_limit)      
        return list(posts) # Consume all items in the generator and return as list

    async def _fetch_subreddit_posts(self, subreddit: str, sorting: str, time: str, post_limit: Optional[int]) -> List[Submission]:
        def to_run() -> List[Submission]:
            sub = reddit.subreddit(subreddit)
            if sorting == "hot":
                posts = sub.hot()
            else:
                posts = sub.top(time_filter=time, limit=post_limit)      
            return list(posts)
        try:
            posts = await self.bot.loop.run_in_executor(None, to_run)
        except (Forbidden, Redirect, NotFound) as e:
            if isinstance(e, Forbidden):
                reason = "Subreddit might be quarantined."
            else:
                reason = "Verify that the subreddit exists and is spelled correctly."
            raise CommandError(f"Cannot retrieve `r/{subreddit}` submissions! {reason}")
        return posts

    async def get_from_reddit(self,
                              ctx: commands.Context,
                              subreddit: str,
                              sorting: str = None,
                              time: str = None,
                              post_limit: int = None,
                              is_text: bool = False,
                              allow_nsfw: bool = False
                            ) -> None:
        # Parse arguments to params sorting & time
        sorting = await self.check_sorting(ctx, sorting) # "top"/"hot"
        time = await self.check_time(ctx, time) # "all", "year", "month", "week", "day"

        # Get post limit
        if post_limit is None:
            post_limit = self.POST_LIMITS.get(time, 25)
        
        # Get Reddit posts from a given subreddit
        # Check if cached submissions exist first
        posts = self.submissions.get(ctx.guild.id, subreddit, sorting, time)
        if not posts:
            async with ctx.message.channel.typing():
                # Fetch new posts and cache them
                posts = await self._fetch_subreddit_posts(subreddit, sorting, time, post_limit)
                self.submissions.add(posts, ctx.guild.id, subreddit, sorting, time)

        # Select a random post from list of posts
        post = await self._get_random_reddit_post(posts, is_text)
        if post is None:
            raise CommandError(f"Failed to find a post within the given parameters for the subreddit **r/{subreddit}**")

        # FIXME: Shitty band-aid fix to support videos
        if post.media:
            return await ctx.send(post.media["reddit_video"]["fallback_url"])

        # Obtain (title, image URL) or (selftext, None) if is_text==True
        out_text, image_url = await self._format_reddit_post(post, subreddit, is_text)

        # Rehost image to discord CDN if image is hosted on Imgur
        # Discord has trouble embedding Imgur images
        if image_url and "imgur" in image_url:
            msg = await self.rehost_image_to_discord(ctx, image_url)
            image_url = msg.attachments[0].url

        # Embed image if image URL is not None
        if image_url:
            await self.send_embed_message(ctx, description="", title=out_text, image_url=image_url, color=self.COG_COLOR)
        else: # Send plain text otherwise
            await self.send_text_message(out_text, ctx)

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
        pfix = self.bot.command_prefix
        return pfix + f", {pfix}".join(aliases+[subreddit]) if aliases else pfix + subreddit
