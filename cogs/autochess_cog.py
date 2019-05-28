import asyncio
from functools import partial

import discord
import requests
import ciso8601
from bs4 import BeautifulSoup
from discord.ext import commands

from cogs.base_cog import BaseCog
from cogs.db_cog import DatabaseHandler
from config import GENERAL_DB_PATH
from utils.caching import get_cached
from utils.converters import SteamID64Converter
from utils.exceptions import CommandError
from utils.serialize import dump_json

USERS_FILE = "db/autochess/users.json"
RANKS = {
    "Pawn 1": 0,
    "Pawn 2": 1,
    "Pawn 3": 2,
    "Pawn 4": 3,
    "Pawn 5": 4,
    "Pawn 6": 5,
    "Pawn 7": 6,
    "Pawn 8": 7,
    "Pawn 9": 8,
    "Knight 1": 9,
    "Knight 2": 10,
    "Knight 3": 11,
    "Knight 4": 12,
    "Knight 5": 13,
    "Knight 6": 14,
    "Knight 7": 15,
    "Knight 8": 16,
    "Knight 9": 17,
    "Bishop 1": 18,
    "Bishop 2": 19,
    "Bishop 3": 20,
    "Bishop 4": 21,
    "Bishop 5": 22,
    "Bishop 6": 23,
    "Bishop 7": 24,
    "Bishop 8": 25,
    "Bishop 9": 26,
    "Rook 1": 27,
    "Rook 2": 28,
    "Rook 3": 29,
    "Rook 4": 30,
    "Rook 5": 31,
    "Rook 6": 32,
    "Rook 7": 33,
    "Rook 8": 34,
    "Rook 9": 35,
    "King": 36,
    "Queen": 37,
}
RANKS_REVERSE = {v: k for k, v in RANKS.items()}

RANK_EMOJIS = {
    "Pawn": "♟️",
    "Knight": "♞",
    "Bishop": "♝",
    "Rook": "♜",
    "King": "♚",
    "Queen": "♛"
}

class AutoChessCog(BaseCog):
    EMOJI = "♟️"
    FILES = [USERS_FILE]
    DIRS = ["db/autochess"]

    DB = DatabaseHandler(GENERAL_DB_PATH)
    
    def __init__(self, bot: commands.Bot) -> None:
        self.setup(default_factory=dict)
        super().__init__(bot)
    
    @property
    def users(self) -> dict:
        return get_cached(USERS_FILE, "autochess")

    def dump_users(self, users: dict) -> None:
        dump_json(USERS_FILE, users)
            
    @commands.group(name="autochess", aliases=["ac", "dac"])
    async def autochess(self, ctx: commands.Context) -> None:
        if not ctx.invoked_with:
            raise CommandError("No subcommand specified!")

    @autochess.command(name="addme")
    async def add_user_self(self, ctx: commands.Context, steamid: SteamID64Converter) -> None:
        """Add yourself to the bot!"""
        await ctx.invoke(self.add_user, steamid, ctx.message.author)

    @autochess.command(name="add")
    async def add_user(self, ctx: commands.Context, steamid: SteamID64Converter, user: commands.MemberConverter=None) -> None:
        """Add a DAC user to the bot."""
        await self._do_add_user(user, steamid)
        await ctx.send(f"Added {user} with SteamID {steamid}!")
    
    async def _do_add_user(self, user: discord.User, steamid: str) -> None:
        rank, matches_played, wins, mmr, last_updated = await self.scrape_op_gg_stats(steamid)
        users = self.users
        users[str(user.id)] = {
                          "steamid": steamid, 
                          "rank": rank,
                          "mmr": mmr, 
                          "matches": matches_played, 
                          "wins": wins,
                          "last_updated": last_updated
                          }
        self.dump_users(users)
    
    async def scrape_op_gg_stats(self, steamid) -> None:
        url = f"https://autochess.op.gg/user/{steamid}"
        
        to_run = partial(requests.get, url)
        r = await self.bot.loop.run_in_executor(None, to_run)

        if r.status_code != 200:
            raise CommandError("No response from stats API.")

        soup = BeautifulSoup(r.text, features="lxml")
        
        # Last updated
        t = soup.find("span", {"class": "date"}).text
        t = t.splitlines()[1].strip()
        last_updated = ciso8601.parse_datetime(t).isoformat()
        
        # Rank
        rank_str = soup.find("h3").text # Knight 7, Bishop 1, Rook 5, etc.
        try:
            # Get integer representation of rank
            rank_int = RANKS[rank_str] # Knight 7 = 15, Bishop 1 = 18, etc.
        except KeyError:
            raise CommandError("Stats API returned invalid data!")
        
        # Matches played
        matches = soup.find("div", {"class": "text-muted"}).text.strip().splitlines()[0].split(" ")[0]
        matches = int(matches)

        # Wins
        wins = 0

        # MMR
        mmr = 0
        
        return rank_int, matches, wins, mmr, last_updated
        
    @autochess.command(name="users")
    async def show_users(self, ctx: commands.Context) -> None:
        
        # Sort players by rank
        _users = sorted(self.users.values(), key=lambda u: u["rank"], reverse=True)
        sorted_users = {}
        for user, vals in zip(self.users, _users):
            if self.users[user] == vals:
                sorted_users[user] = vals
        
        # Format player ranking list
        out = []
        for idx, (user_id, v) in enumerate(sorted_users.items(), start=1):
            name = self.bot.get_user(int(user_id)).name
            rank = RANKS_REVERSE.get(v["rank"])
            rank_emoji = RANK_EMOJIS.get(rank.split(" ")[0], "")

            matches = v['matches']
            out.append(f"**{idx}. {name}**\nRank: {rank_emoji} {rank}\nMatches: {matches}\n")
        out_str = "\n".join(out)
        
        await self.send_embed_message(ctx, "DGVGK Autochess Rankings", out_str)

    @autochess.command(name="update")
    async def update_ranks(self, ctx: commands.Context) -> None:
        await ctx.send("Updating all users... This might take a while")
        for user_id, (steamid, *_) in self.users.items():
            await ctx.invoke(self.add_user, int(user_id), steamid)
            await asyncio.sleep(10) # I need to experiment with this delay
