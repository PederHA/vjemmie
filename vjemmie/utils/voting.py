import asyncio
import inspect
import subprocess
from collections import defaultdict
from contextlib import suppress
from datetime import datetime
from enum import Enum
from typing import Dict, DefaultDict, Optional

import discord
from discord.ext import commands
from discord.ext.commands.errors import BadArgument

from .converters import NonCaseSensMemberConverter
from .exceptions import CommandError



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


class VotingSession:
    """Represents a voting session."""

    def __init__(self,
                 ctx: commands.Context,
                 topic: str,
                 threshold: int, 
                 duration: float,
                 *,
                 loopinterval: int=10,
                 
                ) -> None:
        """
        Parameters
        ----------
        ctx : `discord.ext.commands.Context`
            Discord Context
        threshold : `int`
            Number of votes required to pass the vote.
        duration : `float`
            Duration of voting session in seconds.
        loopinterval : int
            How often to check if session is still active.
        """
        self.ctx: commands.Context = ctx
        self.threshold = threshold
        self.duration = duration
        if loopinterval > duration:
            self.loopinterval = duration / 2          
        else:
            self.loopinterval = loopinterval
            
        self.bot: commands.Bot = ctx.bot
        self.loop: Optional[asyncio.Task] = None
        self.reset()
        self.topic = topic
        self.commandstr = f"`{ctx.bot.command_prefix}{ctx.command.qualified_name} {self.topic}`"
        # TODO: Add superuser vote weighting
        #       Add superuser supervote (triggers action)
    
    def reset(self) -> None:
        """Resets voting session."""
        self.start = datetime.now()
        self.votes: Dict[int, Vote] = {}
        if self.loop:
            self.stop_loop()
    
    def start_loop(self) -> None:
        self.loop = self.bot.loop.create_task(self.sessionloop())

    def stop_loop(self) -> None:
        if self.loop:
            self.loop.cancel()
            self.loop = None
   
    @property
    def votes_remaining(self) -> int:
        return self.threshold - len(self.votes)

    @property
    def current(self) -> int:
        return len(self.votes)

    @property
    def elapsed(self) -> float:
        return (datetime.now() - self.start).total_seconds()

    @property
    def time_remaining_str(self) -> str:
        remaining = self.duration - self.elapsed
        if remaining > 60:
            r = round(remaining/60)
            return f"{r} minute{'s' if r > 1 else ''}"
        else:
            r = round(remaining)
            return f"{r} second{'s' if r > 1 else ''}"

    def __del__(self) -> None:
        """Ensures an active loop is cancelled when object is deleted."""
        with suppress(AttributeError, asyncio.CancelledError):
            self.stop_loop()

    async def sessionloop(self) -> None:
        """Periodically checks if voting session is still active."""
        while True:
            if self.elapsed > self.duration:
                await self.ctx.send(
                    f"Voting session for {self.commandstr} ended. Insufficient votes."
                )
                return await purge_session(self.ctx, self.topic)
            await asyncio.sleep(self.loopinterval)


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

        # Start voting session loop
        if not self.loop:
            self.start_loop()

        if await self.check_votes():
            await ctx.send(f"Sufficient votes received!") # NOTE: remove?
        else:
            s = "s" if self.votes_remaining > 1 else ""
            areis = "are" if self.votes_remaining > 1 else "is"
            await ctx.send(
                f"Vote added! {self.votes_remaining} more vote{s} within the next " 
                f"{self.time_remaining_str} {areis} required.\n"
                f"Type {self.commandstr} to add votes."
            )

    async def _add_vote(self, ctx: commands.Context) -> None:
        self.votes[ctx.message.author.id] = Vote(ctx)

    async def _vote_exists(self, ctx: commands.Context) -> bool:
        """Check if voter has already voted. 
        Sends message to voter's channel if a previous vote exists."""
        if ctx.message.author.id in self.votes:
            minutes = self.duration//60
            if not minutes:
                time_fmt = f"{int(self.duration)} seconds"
            else:
                time_fmt = f"{round(minutes)} minute"
                if minutes > 1:
                    time_fmt += "s"
            await ctx.send(
                f"You have already voted for {self.commandstr} "
                f"within the last {time_fmt}."
            )
        return ctx.message.author.id in self.votes


def vote(votes: int=2, duration: int=300, topic: TopicType=TopicType.default) -> bool:
    async def predicate(ctx):
        if votes < 2: # Can't have a voting session with less than 2 required votes
            return True

        # Make sure an active session exists, otherwise create one
        topicstr = await get_str_topic(ctx, topic)
        try:
            await get_session(ctx, topicstr) # check if a voting session is active
        except KeyError:
            await create_session(ctx, topicstr, votes, duration)
        
        await add_vote(ctx, topicstr)

        session = await get_session(ctx, topicstr)
        if await session.check_votes():
            await purge_session(ctx, topicstr) # delete voting session after completion
        else:
            raise NotEnoughVotes
        return True
    
    return commands.check(predicate)


async def get_str_topic(ctx: commands.Context, topic: TopicType) -> str:
    """This is NOT robust."""
    # "!tt start vjemmie" -> "vjemmie"
    s = ctx.message.content.rsplit(ctx.invoked_with)[-1].strip().lower()
    if topic is TopicType.member:
        member = await NonCaseSensMemberConverter().convert(ctx, s)
        return member.name # member.id instead? Could run into users with identical names
    return s # fall back on s no matter what

# Nested dicts are trash, but really easy to use
# Key 1: Guild ID
# Key 2: Qualified name of command
# Key 3: Voting topic
SessionsType = DefaultDict[int, DefaultDict[str, Dict[str, VotingSession]]]
SESSIONS: SessionsType = defaultdict(lambda: defaultdict(dict)) # don't shoot me for this, please


async def create_session(ctx: commands.Context, topic: str, *args, **kwargs) -> VotingSession:
    session = VotingSession(ctx, topic, *args, **kwargs)
    SESSIONS[ctx.guild.id][ctx.command.qualified_name][topic] = session
    return session


async def get_session(ctx: commands.Context, topic: str) -> VotingSession:
    """Attempts to retrieve a voting session based on context and topic."""
    return SESSIONS[ctx.guild.id][ctx.command.qualified_name][topic]


async def purge_session(ctx: commands.Context, topic: str) -> None:
    """Attempts to delete a voting session based on context and topic."""
    SESSIONS[ctx.guild.id][ctx.command.qualified_name][topic].stop_loop()
    del SESSIONS[ctx.guild.id][ctx.command.qualified_name][topic]


async def add_vote(ctx: commands.Context, topic: str) -> None:
    """Attempts to add a vote to a voting session based on context and topic."""
    sess = await get_session(ctx, topic)
    await sess.add_vote(ctx)
