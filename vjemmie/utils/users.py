from typing import Iterable, List, Optional

import discord
from discord.ext.commands import Bot
from discord.errors import NotFound

async def get_user(bot: Bot, user_id: int) -> Optional[discord.User]:
    """Attempts to get user from bot's own member cache, 
    falls back on fetching from API if user is not cached."""
    try:
        return bot.get_user(user_id) or await bot.fetch_user(user_id)
    except NotFound:
        return None


async def get_users_from_ids(bot: Bot, users: Iterable[int]) -> List[discord.User]:
    """Takes an iterable of user IDs and returns list of `discord.User` objects."""
    return list(filter(None.__ne__, [await get_user(bot, user_id) for user_id in users]))
