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

import trueskill
from ..utils.exceptions import CommandError


class DatabaseConnection:
    def __init__(self, db_path: str, bot: commands.Bot) -> None:
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.cursor: sqlite3.Cursor = self.conn.cursor()
        self.bot = bot # To run synchronous methods in thread pool
        
        # I was planning to add separate read and write locks,
        # but I'm not actually sure if that's safe. 
        # So for now, both read and write locks share the same lock.
        self.rlock = asyncio.Lock()
        self.wlock = self.rlock
        
    async def read(self, meth: Callable[[Any], Any], *args) -> Optional[Any]:
        async with self.rlock:
            return await self.bot.loop.run_in_executor(None, meth, *args)

    async def write(self, meth: Callable[[Any], Any], *args) -> Optional[Any]:
        async with self.wlock:
            def to_run():
                meth(*args)
                self.conn.commit()
            return await self.bot.loop.run_in_executor(None, to_run)

    ##################
    # TIDSTYVERI
    ##################

    async def get_tidstyveri(self) -> List[Tuple[discord.User, float]]:
        return await self.read(self._get_tidstyveri)

    def _get_tidstyveri(self) -> List[Tuple[discord.User, float]]:
        tt: List[Tuple[discord.User, float]] = []
        for row in self.cursor.execute("SELECT * FROM tidstyver"):
            user = self.bot.get_user(row[0])
            if not user:
                continue # Ignore user who can't be found
            tt.append((user, row[1]))

        # Return sorted list of (discord.User, float) tuples
        return sorted(
                tt,
                key=lambda i: i[1],
                reverse=True
        )

    async def get_tidstyveri_by_id(self, user_id: int) -> float:
        res = await self.read(self._get_tidstyveri_by_id, user_id)
        return res[1] if res else 0.0
    
    def _get_tidstyveri_by_id(self, user_id: int) -> float:
        self.cursor.execute("SELECT * FROM tidstyver WHERE id==?", (user_id,))
        return self.cursor.fetchone()

    async def add_tidstyveri(self, member: discord.Member, time: float) -> None:
        return await self.write(self._add_tidstyveri, member, time)

    def _add_tidstyveri(self, member: discord.Member, time: float) -> None:
        self.cursor.execute(
            """INSERT INTO tidstyver (id, time)
	        VALUES (?, ?)
	        ON CONFLICT(id)
	        DO UPDATE SET time=time+?""", 
            (member.id, time, time)
        )

    #########
    # PFM
    #########

    async def get_pfm_memes(self, ctx: commands.Context, topic: str) -> None:
        return await self.read(self._get_pfm_memes)

    def _get_pfm_memes(self) -> None:
        self.cursor.execute("SELECT topic, title, description, content, media_type FROM pfm_memes")
        return list(self.cursor.fetchall())

    #########
    # GAMING
    #########

    async def get_gmoments(self) -> None:
        r = await self.read(self._get_gmoments)
        moments = filter(lambda i: i[1] > 0, r) #  ignore users with 0 occurences
        moments = sorted(moments, key=lambda user: user[1], reverse=True)
        return moments
    
    def _get_gmoments(self) -> List[Tuple[int, int]]:
        self.cursor.execute("SELECT * FROM gm")
        return list(self.cursor.fetchall())

    async def add_gmoment(self, member: discord.Member) -> None:
       await self.write(self._add_gmoment, member)

    def _add_gmoment(self, member: discord.Member) -> None:
        self.cursor.execute(
            """INSERT INTO gm (id, occurences)
	        VALUES (?, 1)
	        ON CONFLICT(id)
	        DO UPDATE SET occurences=occurences+1""",
            (member.id,)
        )

    async def decrement_gmoments(self, member: discord.Member) -> None:
        await self.write(self._decrement_gmoments, member)

    def _decrement_gmoments(self, member: discord.Member) -> None:
        self.cursor.execute(f"SELECT occurences FROM gm WHERE id==?", member.id)
        gmoments = self.cursor.fetchone()
        if gmoments is None or gmoments[0] <= 0: # FIXME: is this a tuple or just an int?
            raise CommandError(f"`{member.name}` has no gaming moments on record!")
        self.cursor.execute(f"UPDATE gmoments SET occurences=occurences-1 WHERE id=={member.id}")

    async def purge_gaming_moments(self, member: discord.Member) -> None:
        await self.write(self._purge_gaming_moments, member)

    def _purge_gaming_moments(self, member: discord.Member) -> None:
        self.cursor.execute(f"DELETE FROM `gmoments` WHERE `id`=={member.id}")

    #########
    # SKRIBBL
    #########

    async def add_skribbl_words(self, member: discord.Member, words: Iterable[str]) -> None:
        await self.write(self._add_skribbl_words, member, words)

    def _add_skribbl_words(self, member: discord.Member, words: Iterable[str]) -> None:
        to_add = [(word, member.id, time.time()) for word in words]
        self.cursor.executemany("INSERT OR IGNORE INTO skribbl (word, submitterID, submittedAt) VALUES (?, ?, ?)", to_add)

    async def get_skribbl_words(self) -> List[Tuple[str]]:
        return await self.read(self._get_skribbl_words)

    def _get_skribbl_words(self) -> List[Tuple[str]]:
        self.cursor.execute("SELECT word FROM skribbl")
        return list(self.cursor.fetchall())

    async def get_skribbl_words_by_user(self, user_id: int) -> List[Tuple[str]]:
        return await self.read(self._get_skribbl_words)

    def _get_skribbl_words_by_user(self, user_id: int) -> List[Tuple[str]]:
        self.cursor.execute("SELECT word FROM skribbl WHERE submitterID==?", user_id)
        return list(self.cursor.fetchall())
    
    async def get_skribbl_word_author(self, word: str) -> Tuple[int, int]:
        return await self.read(self._get_skribbl_word_author, word)

    def _get_skribbl_word_author(self, word: str) -> Tuple[int, int]:
        self.cursor.execute("SELECT submitterID, submittedAt FROM skribbl WHERE word==?", (word,))
        return self.cursor.fetchone()

    async def delete_skribbl_words(self, words: Iterable[str]) -> None:
        await self.write(self._delete_skribbl_words, words)

    def _delete_skribbl_words(self, words: Iterable[str]) -> None:
        self.cursor.executemany("DELETE FROM skribbl WHERE word == ?", [(word,) for word in words])
