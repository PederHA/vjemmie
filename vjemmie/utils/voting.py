import asyncio
import inspect
import subprocess
from datetime import datetime
from typing import Dict
from collections import defaultdict

import discord
from discord.ext import commands

from .exceptions import CommandError


SESSIONS = defaultdict(dict)


class NotEnoughVotes(commands.CheckFailure):
    pass


class Vote:
    """Sort of unused atm."""
    def __init__(self, ctx: commands.Context) -> None:
        self.voter: discord.Member = ctx.message.author
        self.time: datetime = ctx.message.created_at


class VotingSession():
    """Represents a voting session."""

    def __init__(self,
                 ctx: commands.Context,
                 threshold: int, 
                 duration: float,
                ) -> None:
        """
        Parameters
        ----------
        threshold : `int`
            Number of votes required to pass the vote.
        duration : `float`
            Duration of voting session in seconds.
        bot : `commands.Bot`
            Discord Bot instance
        """
        self.threshold = threshold
        self.duration = duration
        self.bot: commands.Bot = ctx.bot
        self.ctx: commands.Context = ctx
        self.loop: asyncio.Task = None
        self.reset()
        self._commandstr = f"{ctx.bot.command_prefix}{ctx.command.qualified_name}"
        # TODO: Add superuser vote weighting
        #       Add superuser supervote (triggers action)
    
    def reset(self) -> None:
        """Resets voting session."""
        self.start = datetime.now()
        self.votes: Dict[int, Vote] = {}
        if self.loop:
            self.bot.loop.create_task(self.stop_loop())

    @property
    def remaining(self) -> int:
        return self.threshold - len(self.votes)

    @property
    def current(self) -> int:
        return len(self.votes)

    @property
    def elapsed(self) -> float:
        return (datetime.now() - self.start).total_seconds()

    async def start_loop(self) -> None:
        self.loop = self.bot.loop.create_task(self.sessionloop())

    async def stop_loop(self) -> None:
        if not self.loop:
            raise AttributeError("No session loop is active.")
        self.loop.cancel()

    async def sessionloop(self, interval: int=10) -> None:
        """Periodically checks if voting session is still active."""
        while True:
            if self.elapsed > self.duration:
                await self.ctx.send(
                    f"Voting session for `{self._commandstr}` ended. Not enough votes.")
                self.reset()
            await asyncio.sleep(interval)

    async def check_votes(self) -> bool:
        """Checks if sufficient votes are reached."""
        return len(self.votes) >= self.threshold    
    
    async def add_vote(self, ctx: commands.Context) -> None:
        """Adds a vote."""
        # Add vote
        if self.elapsed < self.duration: # Check if voting session is active
            if not await self._vote_exists(ctx):
                await self._add_vote(ctx)
            else:
                return # this is a little messy
        else:
            self.reset() # reset voting session
            await self._add_vote(ctx)

        # Start voting session loop
        if not self.loop:
            await self.start_loop()

        if await self.check_votes():
            await ctx.send(f"Sufficient votes received!") # NOTE: remove?
        else:
            s = "s" if self.remaining > 1 else ""
            areis = "are" if self.remaining > 1 else "is"
            await ctx.send(f"Vote added! {self.remaining} more vote{s} within the next {int(self.duration - self.elapsed)}s {areis} required.")

    async def _add_vote(self, ctx: commands.Context) -> None:
        self.votes[ctx.message.author.id] = Vote(ctx)

    async def _vote_exists(self, ctx: commands.Context) -> bool:
        """Check if voter has already voted. 
        Sends message to voter's channel if a previous vote exists."""
        if ctx.message.author.id in self.votes:
            minutes = self.duration//60
            if not minutes:
                time_msg = f"{int(self.duration)} seconds"
            else:
                time_msg = f"{round(minutes)} minute"
                if minutes > 1:
                    time_msg += "s"
            await ctx.send(
                "You have already voted for "
                f"`{self._commandstr}` "
                f"within the last {time_msg}."
            )
        return ctx.message.author.id in self.votes


async def _vote(ctx, votes: int, duration: int):
    name = ctx.command.qualified_name
    gid = ctx.guild.id
    try:
        await SESSIONS[gid][name].add_vote(ctx)
    except KeyError:
        SESSIONS[gid][name] = VotingSession(ctx, votes, duration)
        await SESSIONS[gid][name].add_vote(ctx)


def vote(votes: int=2, duration: int=300):
    async def predicate(ctx):
        if votes < 2: # Can't have a voting session with less than 2 required votes
            return True

        await _vote(ctx, votes, duration)
        
        session = SESSIONS[ctx.guild.id][ctx.command.qualified_name]
        if await session.check_votes():
            del session # delete voting session after completion
        else:
            raise NotEnoughVotes
        return True
    
    return commands.check(predicate)
