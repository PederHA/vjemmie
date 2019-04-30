import random
from functools import partial
from typing import Dict, Iterable, List, Tuple

import discord
import markovify
from discord.ext import commands
from requests_html import HTML, HTMLSession

from cogs.base_cog import BaseCog

import asyncio
import json

session = HTMLSession()
USERS_FILE = "db/twitter/users.json"

class TwitterCog(BaseCog):
    """Twitter commands"""
    
    EMOJI = "<:twitter:572746936658952197>"

    DIRS = ["db/twitter"]
    FILES = [USERS_FILE]

    def __init__(self, bot: commands.Bot) -> None:
        super().__init__(bot)
        # Key: Username, Value: tweet URL, tweet text
        self.tweets: Dict[str, List[Tuple[str, str]]] = {}
        
        # Key: Username, Value: markovify text model
        self.text_models: Dict[str, markovify.NewlineText] = {}
        
        for user in self.get_users():
            self.create_commands(user)
  
    def get_users(self) -> List[str]:
        with open(USERS_FILE, "r") as f:
            return json.load(f)

    def dump_users(self, users: List[str]) -> None:
        with open(USERS_FILE, "w") as f:
            json.dump(users, f)
    
    def create_commands(self, user: str) -> None:
        user = user.lower()
        
        # Make command that fetches random tweet URL
        _u_cmd = asyncio.coroutine(partial(self._twitter_url_cmd, user=user))
        url_cmd = commands.command(name=f"{user}")(_u_cmd)

        # Make command that generates tweet using markov chain
        _m_cmd = asyncio.coroutine(partial(self._twitter_markov_cmd, user=user))
        markov_cmd = commands.command(name=f"{user}_markov", aliases=[f"{user}m"])(_m_cmd)

        self.bot.add_command(url_cmd)
        self.bot.add_command(markov_cmd)

    async def _twitter_url_cmd(self, ctx: commands.Context, user: str) -> None:
        tweets = await self.get_tweets(user)
        await ctx.send(random.choice([tweet[0] for tweet in tweets]))

    async def _twitter_markov_cmd(self, ctx: commands.Context, user: str) -> None:
        await ctx.send(await self.generate_sentence(user))

    @commands.command(name="add_twitter")
    async def add_twitter(self, ctx: commands.Context, user: str) -> None:
        """Add twitter user."""
        try:
            await self.get_tweets(user)
        except Exception as e:
            return await ctx.send(
                f"Can't fetch tweets for {user}. Verify that the user exists!"
                )
        else:
            self._add_user(user)
            await ctx.send(f"Added {user}!")

    def _add_user(self, user: str) -> None:
        users = self.get_users()
        
        if user not in users:
            users.append(user)
            self.create_commands(user)
            self.dump_users(users)

    @commands.command(name="twitters")
    async def show_twitter_users(self, ctx: commands.Context) -> None:
        """Displays added twitter users."""

        users = "\n".join([user for user in self.get_users()])
        
        if not users:
            return await ctx.send("No twitter users added! "
            f"Type {self.bot.command_prefix}add_twitter <user> to add a user"
            )
        
        await self.send_embed_message(ctx, header="Twitter users", text=users)

    # Pending removal
    @commands.command(name="stevend", aliases=["dognonce"])
    async def stevend(self, ctx: commands.Context) -> None:
        tweets = await self.get_tweets("SteveDawson0972")
        await ctx.send(random.choice(tweets[0]))
    
    # Pending removal
    @commands.command(name="stevendm", aliases=["stevendmarkov"])
    async def stevend_markov(self, ctx: commands.Context) -> None:
        await ctx.send(await self.generate_sentence("SteveDawson0972"))

    async def get_tweets(self, user: str) -> List[str]:
        """Retrieves tweets for a specific user.
        
        Checks if user's tweets are cached in TwitterCog.tweets before
        attempting to scrape tweets from user's Twitter page.
        """
        tweets = self.tweets.get(user)
        if tweets:
            return tweets
        
        to_run = partial(self._get_tweets, user, pages=10)
        try:
            tweets = list(
                await self.bot.loop.run_in_executor(None, to_run)
                )
        except Exception as e:
            raise OSError(f"Could not fetch tweets for {user}")
        else:
            self.tweets[user] = tweets
            return tweets

    def _get_tweets(self, user: str, pages: int=10) -> Iterable[str]:
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
                    text = tweet.find('.tweet-text')[0].full_text
                    _url = f"https://twitter.com/{user}/status/{tweet.attrs['data-item-id']}"          
                    tweets.append((_url, text))

                last_tweet = html.find('.stream-item')[-1].attrs['data-item-id']

                for tweet in tweets:
                    if tweet:
                        yield tweet

                r = session.get(
                    url, params = {'max_position': last_tweet}, headers = headers)
                pages += -1

        yield from gen_tweets(pages)
    
    async def generate_sentence(self, user: str, length: int=140) -> str:
        _tweets = await self.get_tweets(user)
        tweets = [tweet[1].split("pic.twitter")[0] for tweet in _tweets]

        text_model = await self.get_text_model(user, tweets)
        
        to_run = partial(text_model.make_short_sentence, 140, tries=300)
        sentence = await self.bot.loop.run_in_executor(None, to_run)
        
        if not sentence:
            raise OSError("Could not generate text!") # I'll find a better exception class

        return sentence
    
    async def get_text_model(self, user: str, text: List[str]) -> markovify.Text:
        text_model = self.text_models.get(user)
        
        if not text_model:
            t = "\n".join([_t for _t in text])
            text_model = markovify.NewlineText(t)
            self.text_models[user] = text_model
        
        return text_model