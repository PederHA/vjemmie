import asyncio
import json
import random
import time
from collections import namedtuple
from functools import partial
from typing import Dict, Iterable, List, Tuple

import discord
import lxml
import markovify
from aiofile import AIOFile
from discord.ext import commands
from requests_html import HTML, HTMLSession

from ..utils.caching import get_cached
from ..utils.exceptions import CommandError
from ..utils.experimental import get_ctx
from ..utils.json import dump_json
from .base_cog import BaseCog

session = HTMLSession()
USERS_FILE = "db/twitter/users.json"

TwitterUser = namedtuple("TwitterUser", "user modified tweets aliases", defaults=[[]])
Tweet = namedtuple("Tweet", "text url")

class TwitterCog(BaseCog):
    """Twitter commands"""

    EMOJI = "<:twitter:572746936658952197>"

    DIRS = ["db/twitter"]
    FILES = [USERS_FILE]

    TWITTER_PAGES = 20
    MARKOV_LEN = 140

    def __init__(self, bot: commands.Bot) -> None:
        super().__init__(bot)
        
        # Key: Username, Value: markovify text model
        self.text_models: Dict[str, markovify.NewlineText] = {}

        for user in self.users.values():
            self.create_commands(user)
        
    @property
    def users(self) -> Dict[str, TwitterUser]:
        users = get_cached(USERS_FILE, category="twitter")
        return {user: TwitterUser(*values) for user, values in users.items()}

    async def update_user(self, user: TwitterUser) -> None:
        self.users[user.user] = user
        await dump_json(USERS_FILE, self.users)

    def create_commands(self, user: TwitterUser) -> None:
        username = user.user.lower()
        aliases = user.aliases

        # Make command that fetches random tweet URL
        _u_cmd = asyncio.coroutine(partial(self._twitter_url_cmd, user=username))
        url_cmd = commands.command(name=f"{username}", aliases=aliases)(_u_cmd)

        # Make command that generates tweet using markov chain
        _m_cmd = asyncio.coroutine(partial(self._twitter_markov_cmd, user=username))
        markov_cmd = commands.command(name=f"{username}_markov", 
                                      aliases=[f"{alias}m" for alias in aliases] or [f"{username}m"]
                                      )(_m_cmd)

        self.bot.add_command(url_cmd)
        self.bot.add_command(markov_cmd)

    async def _twitter_url_cmd(self, ctx: commands.Context, user: str) -> None:
        tweets = self.users[user].tweets
        await ctx.send(random.choice(tweets)[0])

    async def _twitter_markov_cmd(self, ctx: commands.Context, user: str) -> None:
        await ctx.send(await self.generate_sentence(user))
    
    @commands.group(name="twitter", enabled=False)
    async def twitter(self, ctx: commands.Context) -> None:
        cmds = ", ".join([f"**`{command.name}`**" for command in ctx.command.commands])
        if ctx.invoked_subcommand is None:
            await ctx.send(f"No argument provided! Must be one of: {cmds}.")
    
    @twitter.command(name="add")
    async def add_twitter_user(self, ctx: commands.Context, user: str, *aliases) -> None:
        """Add twitter user."""
        await ctx.message.channel.trigger_typing()
        user = user.lower()

        if user in self.users:
            raise CommandError(f"{user} is already added! " 
                f"Type **`{self.bot.command_prefix}twitter update {user}`** to fetch newest tweets for {user}.")

        try:
            await self.get_tweets(ctx, user, aliases=aliases)
        except:
            raise
        else:
            self.create_commands(self.users[user])
            await ctx.send(f"Added {user}!")
  
    @twitter.command(name="update")
    async def update_tweets(self, ctx: commands.Context, user: str) -> None:
        """Update tweets for a specific user."""

        user = user.lower()
        if user in self.users:
            try:
                await self.get_tweets(ctx, user)
            except:
                raise
            else:
                await ctx.send(f"Updated {user} successfully!")
        else:
            await ctx.send("User is not added! "
            f"Type **`{self.bot.command_prefix}twitter add <user>`** or ")
    
    @twitter.command(name="users", aliases=["show", "list"])
    async def show_twitter_users(self, ctx: commands.Context) -> None:
        """Displays added twitter users."""

        users = "\n".join([user for user in self.users])

        if not users:
            return await ctx.send("No twitter users added! "
            f"Type `{self.bot.command_prefix}twitter add <user>` to add a user"
            )

        await self.send_embed_message(ctx, "Twitter users", users)

    async def get_tweets(self, ctx: commands.Context, user: str, aliases=None) -> List[Tuple[str, str]]:
        """Retrieves tweets for a specific user.
        
        If user already has saved tweets, new tweets are added to
        existing list of tweets.
        """
        if not aliases:
            aliases = []
        
        tweets = []
        msg = await ctx.send("Fetching tweets...")
        
        try:
            to_run = partial(self._get_tweets, user, pages=self.TWITTER_PAGES)
            async with ctx.typing():
                tweets = await self.bot.loop.run_in_executor(None, to_run)
        except ValueError:
            raise IOError(f"Unable not fetch tweets for {user}")
        except lxml.etree.ParserError:
            pass
        else:
            if not tweets:
                return
            
            # Add fetched tweets to existing user's tweets if they exist
            _user = self.users.get(user)
            if _user:
                tweets = set(tuple(tweets))
                old_tweets = set(tuple((tweet[0], tweet[1]) for tweet in _user.tweets))
                tweets.update(old_tweets)
                tweets = list(tweets)
                aliases = _user.aliases      
            
            # Create new TwitterUser object with updated tweets
            tu = TwitterUser(user, time.time(), tweets, aliases)
            
            # Save updated user
            await self.update_user(tu)     
        finally:
            await msg.delete()

    def _get_tweets(self, user: str, pages: int) -> Iterable[str]:
        """Modified version of https://github.com/kennethreitz/twitter-scraper.

        Generator of tweet URLs or tweet text from a specific user.
        
        Parameters
        ----------
        user : `str`
            Username of user to get tweets from
        pages : `int`, optional
            Number of pages to return tweets from. 
            25 is the maximum allowed number of pages.
     
        Raises
        ------
        ValueError
            Raised if user cannot be found
        
        Returns
        -------
        `Iterable[str]`
            Tweets
        """

        url = f'https://twitter.com/i/profiles/show/{user}/timeline/tweets?include_available_features=1&include_entities=1&include_new_items_bar=true'
        headers = {
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Referer': f'https://twitter.com/{user}',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/603.3.8 (KHTML, like Gecko) Version/10.1.2 Safari/603.3.8',
            'X-Twitter-Active-User': 'yes',
            'X-Requested-With': 'XMLHttpRequest'
        }

        def gen_tweets(pages: int):
            r = session.get(url, headers=headers)

            while pages > 0:
                try:
                    html = HTML(html=r.json()['items_html'],
                                url='bunk', default_encoding='utf-8')
                except KeyError:
                    raise ValueError(
                        f'Oops! Either "{user}" does not exist or is private.')

                tweets = []
                for tweet in html.find('.stream-item'):
                    try:
                        text = tweet.find('.tweet-text')[0].full_text.split(
                            "pic.twitter.com")[0].split("https://")[0]
                        _url = f"https://twitter.com/{user}/status/{tweet.attrs['data-item-id']}"
                        tweets.append((_url, text))
                    except:
                        pass

                last_tweet = html.find('.stream-item')[-1].attrs['data-item-id']

                for tweet in tweets:
                    if tweet:
                        yield tweet

                r = session.get(
                    url, params = {'max_position': last_tweet}, headers = headers)
                pages += -1

        yield from gen_tweets(pages)

    async def generate_sentence(self, user: str, length: int=140) -> str:
        # Add user if username passed in is not added to database
        if user not in self.users:
            ctx = get_ctx()
            await self.get_tweets(ctx, user)
        
        # Get tweet text only
        tweets = [tweet[1] for tweet in self.users[user].tweets]

        # Create text model based on tweets
        text_model = await self.get_text_model(user, tweets)

        to_run = partial(text_model.make_short_sentence, length, tries=300)
        sentence = await self.bot.loop.run_in_executor(None, to_run)

        if not sentence:
            raise OSError("Could not generate text!") # I'll find a better exception class

        return sentence

    async def get_text_model(self, user: str, text: List[str]) -> markovify.Text:
        # Check if we have already created a text model for this user
        text_model = self.text_models.get(user)

        if not text_model:
            t = "\n".join([_t for _t in text])
            text_model = markovify.NewlineText(t)
            self.text_models[user] = text_model

        return text_model
