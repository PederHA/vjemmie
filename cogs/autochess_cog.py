import asyncio
from functools import partial
from datetime import datetime, timezone

import discord
import requests
import ciso8601
from bs4 import BeautifulSoup
from discord.ext import commands

from cogs.base_cog import BaseCog
from cogs.db_cog import DatabaseHandler
from config import GENERAL_DB_PATH
from utils.caching import get_cached
from utils.converters import SteamID64Converter, UserOrMeConverter
from utils.exceptions import CommandError
from utils.serialize import dump_json
from utils.checks import admins_only
from utils.datetimeutils import format_time_difference

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
    "Pawn": "♙",
    "Knight": "♘",
    "Bishop": "♗",
    "Rook": "♖",
    "King": "♔",
    "Queen": "♕"
}
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36"

class AutoChessCog(BaseCog):
    """Dota Autochess commands."""
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
    @commands.cooldown(rate=1, per=600, type=commands.BucketType.user)
    async def add_user_self(self, ctx: commands.Context, steamid: SteamID64Converter) -> None:
        """Alias for `!add <own user> <steamid>`"""
        await ctx.invoke(self.add_user, ctx.message.author, steamid)

    @autochess.command(name="add")
    @admins_only()
    async def add_user(self, ctx: commands.Context, user: UserOrMeConverter, steamid: SteamID64Converter) -> None:
        """Add a DAC user to the bot."""
        # Make sure OP.GG profile for SteamID is generated and up to date
        try:
            await self.request_opgg_renew(user, steamid)
        except:
            pass
        await asyncio.sleep(5) # Sleep to allow OP.GG time to generate profile
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
        for p in soup.findAll("span", {"class": "date"}):
            if "text-muted" in p.attrs["class"]:
                continue
            if "data-enablefromnow" in p.attrs:
                # This is the "last updated" timestamp
                t = p.attrs["data-date"]
                break
        else:
            raise CommandError("Unable to parse stats!")

        last_updated = ciso8601.parse_datetime(t).isoformat() # NOTE: Not necessary? Just save string from website?
        
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
    
    async def request_opgg_renew(self, user: discord.User, steamid: str) -> None:
        renew_url = f"https://autochess.op.gg/api/user/{steamid}/request-renew"
        to_run = partial(requests.post, renew_url, headers={"User-Agent": USER_AGENT})
        r = await self.bot.loop.run_in_executor(None, to_run)
        if r.status_code != 201:
            raise CommandError(f"Failed to renew stats for {user.name}")
        return r

    @autochess.command(name="users", aliases=["players"])
    async def show_users(self, ctx: commands.Context) -> None:
        """Display all added AutoChess players."""
        
        # Sort players by rank
        # VERY inefficient. TODO: Find better solution
        # NOTE: solution could be to store Discord User ID in values
        _users = sorted(self.users.values(), key=lambda u: u["rank"], reverse=True)
        sorted_users = {}
        for vals in _users:
            for k, v in self.users.items():
                if v == vals:
                    sorted_users[k] = vals
                    break
        
        # Format player ranking list
        out = []
        for idx, (user_id, v) in enumerate(sorted_users.items(), start=1):
            name = self.bot.get_user(int(user_id)).name
            
            rank = RANKS_REVERSE.get(v["rank"])
            
            rank_emoji = RANK_EMOJIS.get(rank.split(" ")[0], "")
            
            matches = v['matches']
            
            # Format datetime.
            _l_u = ciso8601.parse_datetime(v["last_updated"])
            diff = datetime.now(timezone.utc) - _l_u
            
            # Show "x hours/minutes/seconds ago" if <1 day since update
            if diff.days < 1:
                _last_updated = format_time_difference(_l_u, timezone=timezone.utc)
                last_updated = "Just now" # default, in case all time dict values are 0
                for k, v in _last_updated.items():
                    if v < 1:
                        continue
                    if v == 1:
                        k = k[:-1] # "1 hour" instead of "1 hours"
                    last_updated = f"{v} {k} ago"
                    break

            # Show "yesterday" if 1 day since update
            elif diff.days == 1:
                last_updated = "yesterday"
            
            # Show "x days ago" if <=1 week since update
            elif diff.days <= 7:
                last_updated = f"{diff.days} days ago"
            
            # Formatted date (e.g. Thu May 02 2019) if >1 week since last update
            else:
                last_updated = _l_u.strftime("%a %b %d %Y")

            out.append(f"**{idx}. {name}**\n"
                f"Rank: {rank_emoji} {rank}\n"
                f"Matches: {matches}\n"
                f"Last updated: {last_updated}")
        out_str = "\n\n".join(out)
        
        await self.send_embed_message(ctx, "DGVGK Autochess Rankings", out_str)

    @autochess.command(name="update")
    @commands.cooldown(rate=1, per=600, type=commands.BucketType.default)
    async def update_ranks(self, ctx: commands.Context, arg: str=None) -> None:
        """Update a specific user or all users's profiles."""
        # Parse argument
        if not arg or arg in ["help", "?", "h", "--help", "-help"]:
            return await ctx.send(f"""Command usage: **`{self.bot.command_prefix}update <user> or "all"`**.""")
        elif arg in ["all", "everyone", "global"]:
            users = self.users.items()
            await ctx.send("Updating all users... This might take a while")
        else:
            user = await UserOrMeConverter().convert(ctx, arg)
            autochess_data = self.users.get(str(user.id))
            if not autochess_data:
                raise CommandError(f"{user.name} has no AutoChess profile!\n"
                f"You can add this person by typing **`{self.bot.command_prefix}autochess add {user.name} <steamid>`**")
            users = {user.id: autochess_data}
        
        for user_id, v in users:
            user = self.bot.get_user(int(user_id))
            steamid = v["steamid"]
            
            # Send a "renew" request to OP.GG first
            await self.request_opgg_renew(user, steamid)
            
            # Get updated user stats
            await self._do_add_user(user, steamid)
            
            # Sleep for an, as of yet, undetermined amount of time to minimize risk
            # of getting banned for scraping OP.GG's website
            await asyncio.sleep(10) # I need to experiment with delay duration
        
        await ctx.send("Successfully updated all users!")
