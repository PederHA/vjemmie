from typing import Dict

from discord.ext import commands

from ..config import MAIN_DB
from .db import DatabaseConnection

# Maybe this is a little clumsy?
_CONNECTIONS: Dict[str, DatabaseConnection] = {}


def add_db(path: str, bot: commands.Bot) -> DatabaseConnection:
    if path not in _CONNECTIONS:
        _CONNECTIONS[path] = DatabaseConnection(path, bot)
    return _CONNECTIONS[path]


def get_db(path: str=MAIN_DB) -> DatabaseConnection:
    return _CONNECTIONS[MAIN_DB]
