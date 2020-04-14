import asyncio
import inspect
import subprocess
from datetime import datetime
from typing import Dict
from collections import defaultdict
from enum import Enum

import discord
from discord.ext import commands

from .exceptions import CommandError
from .converters import NonCaseSensMemberConverter

# Nested dicts are trash, but really easy to use
SESSIONS = defaultdict(lambda: defaultdict(dict)) # don't shoot me for this, please


class TopicType(Enum):
    default = 0
    member = 1
    # more to come ...


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
                 topic: str
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
        self.topic = topic
        self.loop: asyncio.Task = None
        self.reset()
        self._commandstr = ctx.message.content
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
            await ctx.send(
                f"Vote added! {self.remaining} more vote{s} within the next " 
                f"{int(self.duration - self.elapsed)}s {areis} required.\n"
                f"Type `{self._commandstr}` to add votes."
            )

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


async def _vote(ctx: commands.Context, votes: int, duration: int) -> None:
    qname = ctx.command.qualified_name
    gid = ctx.guild.id
    voted = get_voted_topic(ctx)
    try:
        await SESSIONS[gid][qname][voted].add_vote(ctx)
    except KeyError:
        SESSIONS[gid][qname][voted] = VotingSession(ctx, votes, duration, voted)
        await SESSIONS[gid][qname][voted].add_vote(ctx)


def vote(votes: int=2, duration: int=300, topic: TopicType=TopicType.default) -> bool:
    async def predicate(ctx):
        if votes < 2: # Can't have a voting session with less than 2 required votes
            return True
        name = get_voted_topic(ctx)

        # This raises a BadArgument exception if the member argument is invalid
        # The exception handler in BaseCog will catch this
        if topic is TopicType.member:
            await NonCaseSensMemberConverter().convert(ctx, name)

        await _vote(ctx, votes, duration)
        
        session = SESSIONS[ctx.guild.id][ctx.command.qualified_name][get_voted_topic(ctx)]
        if await session.check_votes():
            del session # delete voting session after completion
        else:
            raise NotEnoughVotes
        return True
    
    return commands.check(predicate)


def get_voted_topic(ctx: commands.Context) -> str:
    """This is NOT robust."""
    # "!tt start vjemmie" -> "vjemmie"
    return ctx.message.content.rsplit(ctx.invoked_with)[-1].strip()


def purge_session(ctx: commands.Context) -> None:
    """Unused."""
    del SESSIONS[ctx.command.qualified_name][ctx.guild.id][get_voted_topic(ctx)]


def get_session(ctx: commands.Context) -> VotingSession:
    """Unused."""
    return SESSIONS[ctx.guild.id][ctx.command.qualified_name][get_voted_topic(ctx)]