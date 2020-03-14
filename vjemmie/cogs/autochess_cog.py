import asyncio
from functools import partial
from datetime import datetime, timezone
from typing import Union, Tuple, Dict
from dataclasses import dataclass

import discord
import requests
import ciso8601
from bs4 import BeautifulSoup
from discord.ext import commands

from .base_cog import BaseCog
from ..config import ALL_ARGS, YES_ARGS
from ..utils.caching import get_cached
from ..utils.converters import SteamID64Converter, UserOrMeConverter
from ..utils.exceptions import CommandError
from ..utils.serialize import dump_json
from ..utils.checks import admins_only
from ..utils.datetimeutils import format_time_difference

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

@dataclass
class AutochessProfile:
    steamid: Union[str, int] = None
    userid: int = 0
    rank: int = 0
    mmr: int = 0
    matches: int = 0
    wins: int = 0
    wins_recent30: int = 0
    top3_recent30: int = 0
    average_rank: float = 0.0
    last_updated: str = ""
    
    def format_stats(self, bot: commands.Bot, *, rank_n: int=None, show_updated: bool=False, full: bool=False) -> str:
        """Creates a formatted string from a user's AutoChess stats.

        NOTE
        ----
        I am looking for a more elegant solution than passing in the bot instance.
        Potential solutions:

        1. Make `name` a kw-only arg, and falling back on User ID if
           no name is passed into `format_stats()`.
        2. Add Discord username as an AutochessProfile constructor
           parameter.
        """
        
        # Leaderboard rank if passed in
        r = f"{rank_n}. " if rank_n else ""

        # Discord username
        name = bot.get_user(int(self.userid)).name

        # Rank in text-form e.g. "Knight 7"
        rank = RANKS_REVERSE.get(self.rank)

        # Unicode char representing rank e.g. "♘"
        rank_emoji = RANK_EMOJIS.get(rank.split(" ")[0], "")

        # Time since last stats profile update
        if show_updated:
            last_updated = f"\nLast updated: {self._format_last_updated()}"
        else:
            last_updated = ""

        # Additional stats
        if full:
            f = (f"\nWins (recent 30): {self.wins_recent30}\n"
                 f"Top 3 (recent 30): {self.top3_recent30}\n"
                 f"Average placement: #{self.average_rank}")
        else:
            f = ""

        out = (
            f"**{r}{name}**\n"
            f"Rank: {rank_emoji} {rank}\n"
            f"Matches: {self.matches}"
            f"{f}"
            f"{last_updated}"
            )

        return out

    def _format_last_updated(self) -> str:
        # Format datetime.
        _l_u = ciso8601.parse_datetime(self.last_updated)
        diff = datetime.now(timezone.utc) - _l_u

        # Show "x {hours/minutes/seconds} ago" if <1 day since update
        if diff.days < 1:
            _last_updated = format_time_difference(_l_u, tz=timezone.utc)
            # Choose largest time unit, then break
            for k, v in _last_updated.items():
                if v < 1:
                    continue
                if v == 1:
                    k = k[:-1] # "1 hour" instead of "1 hours"
                last_updated = f"{v} {k} ago"
                break
            else:
                # default, in case all time dict values are 0
                last_updated = "just now" 
        
        # Show "yesterday" if 1 day since update
        elif diff.days == 1:
            last_updated = "yesterday"

        # Show "x days ago" if <=1 week since update
        elif diff.days <= 7:
            last_updated = f"{diff.days} days ago"

        # Formatted date (e.g. Thu May 02 2019) if >1 week since last update
        else:
            last_updated = _l_u.strftime("%a %b %d %Y")

        return last_updated


class AutoChessCog(BaseCog):
    """Dota Autochess commands."""
    EMOJI = "♟️"
    FILES = [USERS_FILE]
    DIRS = ["db/autochess"]

    @property
    def users(self) -> Dict[str, AutochessProfile]:
        users = {}
        _users_raw = get_cached(USERS_FILE, "autochess")
        for k, v in _users_raw.items():
            users[k] = AutochessProfile(**v)
        return users

    def dump_users(self, users: dict) -> None:
        dump_json(USERS_FILE, users, default=lambda o: o.__dict__)

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
        # Attempt to update OP.GG profile before fetching stats
        try:
            await self.request_opgg_renew(user, steamid)
        except:
            pass
        await asyncio.sleep(5) # Sleep to allow OP.GG time to generate profile
        await self._do_add_user(user, steamid)
        await ctx.send(f"Added {user} with SteamID {steamid}!")

    async def _do_add_user(self, user: discord.User, steamid: str) -> None:
        profile = await self.scrape_op_gg_stats(steamid, user.id)
        users = self.users
        users[str(user.id)] = profile
        self.dump_users(users)

    async def scrape_op_gg_stats(self, steamid, userid) -> AutochessProfile:
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
                last_updated = p.attrs["data-date"]
                break
        else:
            raise CommandError("Unable to parse stats!")

        # Rank
        _rank_str = soup.find("h3").text # Knight 7, Bishop 1, Rook 5, etc.
        # Get rank as integer, so we can sort players by rank more easily
        try:
            rank = RANKS[_rank_str] # Knight 7 = 15, Bishop 1 = 18, etc.
        except KeyError:
            raise CommandError("Stats API returned invalid data!")

        # Average rank
        average_rank = float(soup.find("span", {
            "class": "content",
            "style": "color:#202d37;"
        }).text.split("#")[1].splitlines()[0])

        # Wins in recent 30 games
        wins_recent30 = int(soup.find("span", {
            "class": "content",
            "style": "color:#5383e8"
        }).text.splitlines()[0])

        # Top 3 recent 30 games
        top3_recent30 = int(soup.find("span", {
            "class": "content",
            "style": "color:#00bba3"
        }).text.splitlines()[0])

        # Matches played
        matches = int(soup.find("div", {
                "class": "text-muted"
            }).text.strip().splitlines()[0].split(" ")[0])

        # Wins
        wins = 0

        # MMR
        mmr = 0

        profile = AutochessProfile(
            steamid=steamid,
            userid=userid,
            rank=rank,
            mmr=mmr,
            matches=matches,
            wins=wins,
            wins_recent30=wins_recent30,
            top3_recent30=top3_recent30,
            average_rank=average_rank,
            last_updated=last_updated
        )

        return profile

    async def request_opgg_renew(self, user: discord.User, steamid: str) -> None:
        renew_url = f"https://autochess.op.gg/api/user/{steamid}/request-renew"
        to_run = partial(requests.post, renew_url, headers={"User-Agent": USER_AGENT})
        r = await self.bot.loop.run_in_executor(None, to_run)
        if r.status_code != 201:
            raise CommandError(f"Failed to renew stats for {user.name}")

    @autochess.command(name="users", aliases=["players", "leaderboard"])
    async def show_users(self, ctx: commands.Context, full: str=None) -> None:
        """Display leaderboard for added AC players."""
        full = full in YES_ARGS + ["full", "complete", "f"]

        # Sort users by rank
        users = sorted(self.users.values(), key=lambda u: u.rank, reverse=True)
        rank_1_user = self.bot.get_user(users[0].userid)

        # Format player ranking list
        out = []
        for idx, user in enumerate(users, start=1):
            user_stats_fmt = user.format_stats(self.bot, rank_n=idx, full=full)
            out.append(user_stats_fmt)
        out_str = "\n\n".join(out)

        await self.send_embed_message(ctx, "DGVGK Autochess Rankings", out_str, thumbnail_url=rank_1_user.avatar_url._url)

    @autochess.command(name="stats")
    async def show_stats(self, ctx: commands.Context, user: str=None) -> None:
        """Show stats for a single user."""
        # Get user
        user = await UserOrMeConverter().convert(ctx, user)
        
        # Attempt to get AutochessProfile object for specified user
        user_stats: AutochessProfile = self.users.get(str(user.id))
        
        # Prompt command invoker to add user if the user is not found.
        if not user_stats:
            raise CommandError(f"**{user}** has no associated AutoChess profile!\n"
            f"To add this user:  `{self.bot.command_prefix}autochess add {user} <steamid>`")
        
        stats = user_stats.format_stats(self.bot, show_updated=True, full=True)
        await self.send_embed_message(ctx, "AutoChess Stats", stats, thumbnail_url=user.avatar_url._url)

    @autochess.command(name="update")
    @commands.cooldown(rate=1, per=600, type=commands.BucketType.default)
    async def update_ranks(self, ctx: commands.Context, arg: str=None) -> None:
        """Update a specific user or all users."""
        # Parse argument
        # Send command help text
        if not arg or arg in ["help", "?", "h", "--help", "-help"]:
            self.reset_command_cooldown(ctx)
            return await ctx.send(f"""Command usage: **`{self.bot.command_prefix}update <user> or "all"`**.""")
        # Update all users
        elif arg in ALL_ARGS:
            users = self.users
            await ctx.send("Updating all users... This might take a while", delete_after=10.0)
        # Update single user
        else:
            # Attempt to get user. Reset cmd cooldown if user is not found
            try:
                user = await UserOrMeConverter().convert(ctx, arg)
            except Exception as e:
                await self.cog_command_error(ctx, e)
                return self.reset_command_cooldown(ctx)

            autochess_data = self.users.get(str(user.id))
            if not autochess_data:
                raise CommandError(f"{user.name} has no AutoChess profile!\n"
                f"You can add this person by typing **`{self.bot.command_prefix}autochess add {user.name} <steamid>`**")
            users = {user.id: autochess_data}

        # Update chosen users
        msg = None
        for idx, (user_id, v) in enumerate(users.items(), start=1):
            if msg:
                await msg.delete()
            msg = await ctx.send(f"Updating user {idx} of {len(users)}")
            user = self.bot.get_user(int(user_id))
            steamid = v.steamid

            # Send a "renew" request to OP.GG first
            try:
                await self.request_opgg_renew(user, steamid)
            except:
                pass  # Renew fails if profile is already up-to-date

            # Get updated user stats
            await self._do_add_user(user, steamid)

            # Sleep for an, as of yet, undetermined amount of time to minimize risk
            # of getting banned for scraping OP.GG's website
            await asyncio.sleep(10)
        else:
            if msg:
                await msg.delete()
        
        if arg in ALL_ARGS:
            u = "all users"
        else:
            u = user.name
        await ctx.send(f"Successfully updated {u}!")
