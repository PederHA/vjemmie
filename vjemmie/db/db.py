"""
Not technically cog, but who's gonna fucking arrest me, huh?
"""

import asyncio
import copy
import datetime
import os
import random
import sqlite3
import time
import traceback
from collections import namedtuple
from typing import Tuple, List, Dict, Callable, Any, Optional, Iterable

import discord
from discord.ext import commands
import aiomysql
from discord.ext.commands.core import Command
import httpx
from .models import (
    GamingMoments,
    GoodmorningTarget,
    MediaType,
    PFMMeme,
    SkribblAdd,
    SkribblAggregateStats,
    SkribblWord,
    Subreddit,
    SubredditAlias,
    Tidstyv,
    Goodmorning,
)

import trueskill
from ..utils.exceptions import CommandError
from ..utils import http

os.environ.setdefault("MYSQL_DB_HOST", "127.0.0.1")
os.environ["MYSQL_ROOT_USER"] = "root"
os.environ["MYSQL_ROOT_PASSWORD"] = "password"


class RESTClient:
    def __init__(self, api_url: str) -> None:
        self.url = api_url

    async def _check_response(
        self, response: httpx.Response, content_type: str = "application/json"
    ) -> None:
        if not response.headers.get("content-type") == content_type:
            raise CommandError("Invalid response type received from API.")

    ##################
    # TIDSTYVERI
    ##################

    async def get_tidstyveri(self) -> List[Tidstyv]:
        resp = await http.get(f"{self.url}/tidstyveri")
        if resp.is_error:
            raise CommandError("Unable to get tidstyver.")
        await self._check_response(resp)
        return [Tidstyv(**t) for t in resp.json()]

    async def get_tidstyveri_by_id(self, user_id: int) -> float:
        resp = await http.get(f"{self.url}/tidstyveri/{user_id}")
        if resp.is_error:
            raise CommandError("Unable to get tidstyver.")
        await self._check_response(resp)
        t = Tidstyv(**(resp.json()))
        return t.stolen

    async def add_tidstyveri(self, member: discord.Member, stolen: float) -> Tidstyv:
        resp = await http.post(
            f"{self.url}/tidstyveri", json={"user_id": member.id, "stolen": stolen}
        )
        if resp.is_error:
            raise CommandError(f"Unable to add tidstyveri for `{member.display_name}`")
        await self._check_response(resp)
        return Tidstyv(**(resp.json()))

    #########
    # PFM
    #########
    # TODO: check if we can delete ctx and topic param
    async def get_pfm_memes(self, ctx: commands.Context, topic: str) -> List[PFMMeme]:
        resp = await http.get(f"{self.url}/pfm/memes")
        if resp.is_error:
            raise CommandError("Unable to retrieve PFM memes.")
        await self._check_response(resp)
        return [PFMMeme(**t) for t in resp.json()]

    async def get_pfm_memes_for_topic(self, topic: str) -> List[PFMMeme]:
        resp = await http.get(f"{self.url}/pfm/memes?topic={topic}")
        if resp.is_error:
            raise CommandError("Unable to retrieve PFM memes.")
        await self._check_response(resp)
        return [PFMMeme(**t) for t in resp.json()]

    #########
    # GAMING
    #########

    async def get_gmoments(self) -> List[GamingMoments]:
        resp = await http.get(f"{self.url}/gamingmoments")
        if resp.is_error:
            raise CommandError("Unable to get gamingmoments.")
        await self._check_response(resp)
        return [GamingMoments(**g) for g in resp.json()]

    async def add_gmoment(self, member: discord.Member) -> None:
        resp = await http.post(f"{self.url}/gamingmoments/{member.id}")
        if resp.is_error:
            raise CommandError(
                f"Unable to add gamingmoment for `{member.display_name}`"
            )
        await self._check_response(resp)
        return GamingMoments(**(resp.json()))

    async def decrement_gmoments(self, member: discord.Member) -> None:
        resp = await http.post(f"{self.url}/gamingmoments/{member.id}?decrease=1")
        if resp.is_error:
            raise CommandError(
                f"Unable to decrease gamingmoments for `{member.display_name}`"
            )
        await self._check_response(resp)
        return GamingMoments(**(resp.json()))

    async def purge_gmoments(self, member: discord.Member) -> None:
        resp = await http.delete(f"{self.url}/gamingmoments/{member.id}")
        if resp.is_error:
            raise CommandError(
                f"Unable to delete gamingmoments for `{member.display_name}`"
            )
        await self._check_response(resp)
        return GamingMoments(**(resp.json()))

    #########
    # SKRIBBL
    #########

    async def add_skribbl_words(
        self, member: discord.Member, words: Iterable[str]
    ) -> SkribblAdd:
        payload = {"words": words, "submitter": member.id}
        resp = await http.post(f"{self.url}/skribbl/words", json=payload)
        if resp.is_error:
            raise CommandError(f"Unable to add Skribbl words.")
        await self._check_response(resp)
        return SkribblAdd(**(resp.json()))

    async def get_skribbl_words(self, limit: Optional[int] = None) -> List[SkribblWord]:
        resp = await http.get(
            f"{self.url}/skribbl/words", params={"limit": limit} if limit else {}
        )
        if resp.is_error:
            raise CommandError(f"Unable to retrieve Skribbl words.")
        await self._check_response(resp)
        return [SkribblWord(**s) for s in resp.json()]

    async def get_skribbl_words_by_user(self, user_id: int) -> List[SkribblWord]:
        resp = await http.get(f"{self.url}/skribbl/words?user_id={user_id}")
        if resp.is_error:
            raise CommandError(f"Unable to retrieve Skribbl words.")
        await self._check_response(resp)
        return [SkribblWord(**s) for s in resp.json()]

    async def get_skribbl_word(self, word: str) -> SkribblWord:
        resp = await http.get(f"{self.url}/skribbl/words/{word}")
        if resp.is_error:
            raise CommandError(f"Unable to find {word}")
        await self._check_response(resp)
        return SkribblWord(**(resp.json()))

    async def delete_skribbl_words(self, words: Iterable[str]) -> None:
        for word in words:
            await http.delete(f"{self.url}/skribbl/words/{word}")

    async def skribbl_get_stats(self) -> SkribblAggregateStats:
        resp = await http.get(f"{self.url}/skribbl/stats-aggregate")
        if resp.is_error:
            raise CommandError(f"Unable to goodmorning target.")
        await self._check_response(resp)
        return SkribblAggregateStats(**(resp.json()))

    async def goodmorning_get_all_targets(self) -> List[Goodmorning]:
        resp = await http.get(f"{self.url}/goodmorning/all")
        if resp.is_error:
            raise CommandError(f"Unable to retrieve goodmorning targets")
        await self._check_response(resp)
        return [GoodmorningTarget(**t) for t in resp.json()]

    async def goodmorning_get_random_target(self) -> GoodmorningTarget:
        resp = await http.get(f"{self.url}/goodmorning")
        if resp.is_error:
            raise CommandError(f"Unable to retrieve skribbl stats")
        await self._check_response(resp)
        return GoodmorningTarget(**(resp.json()))

    async def goodmorning_add_target(
        self, submitter: discord.User, target: str
    ) -> bool:
        resp = await http.post(
            f"{self.url}/goodmorning",
            json={"submitter": submitter.id, "target": target},
        )
        if resp.is_error:
            if resp.status_code == 400:
                raise CommandError(f"{target} has already been added!")
            else:
                raise CommandError(f"Unable to add {target}")
        await self._check_response(resp)
        return Goodmorning(**(resp.json()))

    async def reddit_get_subreddits(self) -> List[Subreddit]:
        resp = await http.get(f"{self.url}/reddit/subreddits")
        if resp.is_error:
            raise CommandError(f"Unable to retrieve subreddits.")
        await self._check_response(resp)
        return [Subreddit(**s) for s in resp.json()]

    async def reddit_get_subreddit(self, subreddit: str) -> Subreddit:
        resp = await http.get(f"{self.url}/reddit/subreddits/{subreddit}")
        if resp.is_error:
            raise CommandError(f"Unable to retrieve subreddit {subreddit}.")
        await self._check_response(resp)
        return Subreddit(**(resp.json()))

    async def reddit_add_subreddit(self, subreddit: Subreddit) -> None:
        resp = await http.post(
            f"{self.url}/reddit/subreddits",
            json=subreddit.dict(),
        )
        if resp.is_error:
            raise CommandError(f"Unable to add subreddit {subreddit.subreddit}.")

    async def reddit_remove_subreddit(self, subreddit: str) -> None:
        resp = await http.delete(f"{self.url}/reddit/subreddits/{subreddit}")
        if resp.is_error:
            raise CommandError(f"Unable to delete subreddit {subreddit}.")
