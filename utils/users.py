from typing import Iterable, List

import discord
from discord.ext.commands import Bot

def get_users_from_ids(bot: Bot, users: Iterable[int]) -> List[discord.User]:
    """Takes an iterable of user IDs and returns list of `discord.User` objects."""
    return list(filter(None.__ne__, [bot.get_user(user) for user in users]))
