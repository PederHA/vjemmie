from collections import defaultdict
from typing import DefaultDict, Optional, Union

from config import TRUSTED_PATH
from utils.caching import get_cached
from utils.serialize import dump_json

T = DefaultDict[int, list]

def _get_trusted() -> T:
    return defaultdict(list, get_cached(TRUSTED_PATH))


def get_trusted_users(guild_id: int) -> list:
    trusted = _get_trusted()
    return trusted[str(guild_id)]


def add_trusted_user(guild_id: int, user_id: int) -> None:
    """Add a trusted user in a specific guild."""
    trusted = _get_trusted()
    
    if user_id in trusted[str(guild_id)]:
        return
    
    trusted[str(guild_id)].append(user_id)

    _dump_trusted(trusted)


def remove_trusted_user(guild_id: int, user_id: int, exist_ok: bool=False) -> None:
    """Remove a trusted user in a specific guild."""
    trusted = _get_trusted()
    try:
        trusted[str(guild_id)].remove(user_id)
    except ValueError:
        if not exist_ok:
            raise
    else:
        _dump_trusted(trusted)


def _dump_trusted(trusted: T) -> None:
    dump_json(TRUSTED_PATH, trusted)
