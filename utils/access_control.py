from collections import defaultdict
from typing import DefaultDict, Optional, Union
from enum import Enum
from functools import partial

from config import TRUSTED_PATH
from utils.caching import get_cached
from utils.serialize import dump_json


DEFAULT = list

class Categories(Enum):
    MEMBER = "members"
    ROLE = "roles"


def _get_trusted() -> dict:
    return defaultdict(partial(defaultdict, DEFAULT), get_cached(TRUSTED_PATH))


def _dump_trusted(trusted: dict) -> None:
    dump_json(TRUSTED_PATH, trusted)


def _get_trusted_guild_category(guild_id: int, category: Categories) -> list:
    try:
        return _get_trusted()[str(guild_id)][category.value]
    except KeyError:
        return DEFAULT()    


def get_trusted_members(guild_id: int) -> list:
    """Get a list of trusted members for a guild."""
    return _get_trusted_guild_category(guild_id, Categories.MEMBER)


def get_trusted_roles(guild_id: int) -> list:
    """Get a list of trusted roles for a guild."""
    return _get_trusted_guild_category(guild_id, Categories.ROLE)


def add_trusted_member(guild_id: int, user_id: int) -> None:
    """Add a trusted member for a guild."""
    _add_trusted(guild_id, user_id, category=Categories.MEMBER)


def add_trusted_role(guild_id: int, role_id: int) -> None:
    """Add a trusted role for a guild."""
    _add_trusted(guild_id, role_id, category=Categories.ROLE)


def _add_trusted(guild_id: int, id_: int, category: str=Categories.MEMBER, *, exist_ok: bool=True) -> None:
    trusted = _get_trusted()
    
    try:
        if id_ in trusted[str(guild_id)][category.value]:
            if not exist_ok:
                raise ValueError(f"{id_} has already been added!")
            return
    except KeyError:
        trusted[str(guild_id)][category.value] = DEFAULT()
    finally:
        trusted[str(guild_id)][category.value].append(id_)

    _dump_trusted(trusted)


def remove_trusted_member(guild_id: int, user_id: int, **kwargs) -> None:
    """Remove a trusted member for a guild."""
    _remove_trusted(guild_id, user_id, category=Categories.MEMBER, **kwargs)


def remove_trusted_role(guild_id: int, role_id: int, **kwargs) -> None:
    """Remove a trusted role for a guild."""
    _remove_trusted(guild_id, role_id, category=Categories.ROLE, **kwargs)


def _remove_trusted(guild_id: int, user_id: int, category: str=Categories.MEMBER, *, exist_ok: bool=False) -> None:
    trusted = _get_trusted()
    try:
        trusted[str(guild_id)][category.value].remove(user_id)
    except ValueError:
        if not exist_ok:
            raise
    else:
        _dump_trusted(trusted)

