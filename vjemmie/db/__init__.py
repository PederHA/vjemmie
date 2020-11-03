from typing import Dict
from pathlib import Path

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


def init_db(path: str, bot: commands.Bot):
    p = Path(MAIN_DB)
    
    # Create db if it doesn't exist
    if not p.exists():
        # NOTE: assumes the database file resides in a subdirectory 
        #       within the project root
        #
        # TODO: Actually make this not completely explode if the db file resides in
        #       the root directory.
        p.parent.mkdir(parents=True, exist_ok=True)
        p.touch()

    # Connect to DB
    db = add_db(path, bot)

    # Add tables (if not already exists)
    with open("db/vjemmie.db.sql", "r") as f:
        script = f.read()
    db.cursor.executescript(script)
