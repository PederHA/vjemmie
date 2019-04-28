import random
import re
from datetime import datetime
from functools import partial
from typing import Iterable

import discord
from discord.ext import commands
from requests_html import HTML, HTMLSession

from cogs.base_cog import BaseCog, EmbedField

session = HTMLSession()

class MemeCog(BaseCog):
    """Text meme commands"""

    EMOJI = ":spaghetti:"

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

    @commands.command(name="stevend", aliases=["dognonce"])
    async def stevend(self, ctx: commands.Context) -> None:
        to_run = partial(self.get_tweets, "SteveDawson0972", pages=10)
        try:
            tweets = list(await self.bot.loop.run_in_executor(None, to_run))
        except:
            await ctx.send("Could not fetch tweets")
        else:
            await ctx.send(random.choice(tweets))

    def get_tweets(self, user: str, pages: int=10, text: bool=False) -> Iterable[str]:
        """Modified version of https://github.com/kennethreitz/twitter-scraper.

        Generator of tweet URLs or tweet text from a specific user.
        
        Parameters
        ----------
        user : `str`
            Username of user to get tweets from
        pages : `int`, optional
            Number of pages to return tweets from. 
            25 is the maximum allowed number of pages.
        text : `bool`, optional
            Return tweet text instead of tweet URL
        
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

        def gen_tweets(pages: int, text: bool):
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
                    if text:
                        t = tweet.find('.tweet-text')[0].full_text
                    else:
                        t = f"https://twitter.com/{user}/status/{tweet.attrs['data-item-id']}"          
                    tweets.append(t)

                last_tweet = html.find('.stream-item')[-1].attrs['data-item-id']

                for tweet in tweets:
                    if tweet:
                        yield tweet

                r = session.get(
                    url, params = {'max_position': last_tweet}, headers = headers)
                pages += -1

        yield from gen_tweets(pages, text)
