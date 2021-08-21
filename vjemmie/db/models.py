from datetime import datetime
from typing import List, Optional, Union

import discord
from discord.ext import commands
from pydantic import BaseModel, Field, validator
from vjemmie.utils.exceptions import FatalBotException
from vjemmieapi.schemas import (
    GamingMomentsOut,
    PFMMemeOut,
    SkribblOut,
    SkribblIn,
    SkribblAddOut,
    SkribblAggregateStats,
    SkribblAuthorStats,
)
from vjemmieapi import schemas

UserMemberT = Optional[Union[discord.User, discord.Member]]

_BOT: Optional[commands.Bot] = None


def init_pydantic_validator(bot: commands.Bot) -> None:
    global _BOT
    _BOT = bot


def pydantic_validator_is_initialized() -> bool:
    return _BOT is not None


class DiscordUserEncoder(BaseModel):
    """Serializes discord.User and discord.Member objects to their user IDs."""

    user: UserMemberT

    @validator("user")
    def validate_user_or_user_id(
        cls, v: Union[UserMemberT, str, int]
    ) -> Optional[discord.User]:
        """Validates a user or user id object. Returns a `discord.User` if found."""
        if isinstance(v, (discord.User, discord.Member)) or v is None:
            return v
        if isinstance(v, str):
            try:
                v = int(v)
            except TypeError:
                raise ValueError("User argument must be a number")
        # v is an int
        if _BOT is None:
            raise FatalBotException("Bot is not set up to validate Pydantic models!")
        return _BOT.get_user(v)

    # _validate_user = validator("user", pre=True, allow_reuse=True, check_fields=False)(
    #     validate_user_or_user_id
    # )

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {
            discord.User: lambda v: v.id,
            discord.Member: lambda v: v.id,
        }


#########################################################################################
#                                                                                       #
# Classes _MUST_ inherit from a VJEmmieAPI model FIRST then DiscordUserEncoder SECOND   #
#                                                                                       #
#########################################################################################


class GamingMoments(schemas.GamingMomentsOut, DiscordUserEncoder):
    pass


class PFMMeme(schemas.PFMMemeOut):
    pass


class SkribblWord(schemas.SkribblOut, DiscordUserEncoder):
    pass


class SkribblAdd(schemas.SkribblAddOut):
    pass


class SkribblAggregateStats(schemas.SkribblAggregateStats):
    pass


class Tidstyv(schemas.TidstyvOut, DiscordUserEncoder):
    pass


class Subreddit(schemas.SubredditOut, DiscordUserEncoder):
    submitted: Optional[datetime]

    def get_aliases(self) -> List[str]:
        a = [a.alias for a in self.aliases]
        if self.subreddit in a:
            a.remove(self.subreddit)
        return a


class SubredditAlias(schemas.SubredditAliasOut):
    pass


class Goodmorning(schemas.GoodmorningOut, DiscordUserEncoder):
    submitted: Optional[datetime]


class MediaType(schemas.MediaTypeOut):
    pass


class GoodmorningTarget(BaseModel):
    target: str
