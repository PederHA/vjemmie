import json
import os
import time
from typing import Any, Dict, Union, Tuple
from collections import deque, defaultdict, OrderedDict
from functools import partial

from recordclass import recordclass
from recordclass.recordobject import recordclasstype


class CacheError(Exception):
    """Exceptions stemming from operations 
    performed on the cache data structure"""

DEFAULT_CATEGORY = "default"
MAX_SIZE = 5

CACHE = None
CachedContent = recordclass("CachedContent", "contents content_type modified")

def get_cached(path: str, category: str=None) -> Union[str, dict, list]:
    """Get contents of a file. 
    The file contents are cached in memory, and all subsequent calls
    to `get_cached()` with identical `path` & `category` arguments
    return cached contents rather than reading the file on disk.

    Should the file be modified between calls, `get_cached()` loads new
    version of file into the cache, overwriting the previous version.
    
    Parameters
    ----------
    path : `str`
        Path + filename
    category : `str`, optional
        Category to cache file under, by default None
        Uses default category if None is passed in.
        The default category "default" can be overridden
        by calling `setup(default=<your category here>)`.
    
    Returns
    -------
    `Union[str, dict, list]`
        Contents of the file, as list or dict if filetype is .json,
        otherwise str.
    """
    # Setup cache if none exists
    if not CACHE:
        _do_create_cache()

    # Fall back on default category
    if not category:
        category = DEFAULT_CATEGORY

    # Attempt to get cached version of file
    cached = _get_from_cache(path, category)

    # Get modification time of cached content if it exists
    if cached:
        last_modified = cached.modified

    # Get current modification time of file
    modified = os.path.getmtime(path)

    # Get file contents on disk if cached file differs or does not exist
    if not cached or last_modified != modified:
        extension = os.path.splitext(path)[1]
        is_json = extension == ".json"
        cache_data = _get_file_contents(path, category, is_json)
        _add_to_cache(path, category, cache_data)
        contents = cache_data.contents

    # Otherwise return cached content
    else:
        contents = cached.contents

    return contents


def _get_file_contents(path: str, category: str, is_json: bool) -> CachedContent:
    """Retrieves content of a file and returns `CachedContent` object."""
    with open(path, "r") as f:
        if is_json:
            contents = json.load(f)
        else:
            contents = f.read()
    modified = os.path.getmtime(path)
    content_type = "json" if is_json else "text"
    return CachedContent(contents, content_type, modified)


def _add_to_cache(path: str, category: str, contents: CachedContent) -> None:
    """Adds contents of a file to the cache."""
    try:
        del CACHE[category][path]
    except KeyError:
        pass
    if len(CACHE[category]) == MAX_SIZE:
        CACHE[category].popitem(last=False) # Pop oldest item
    CACHE[category][path] = contents


def _get_from_cache(path: str, category: str) -> CachedContent:
    """Attempts to retrieve cached contents of a specific filepath + category"""
    try:
        return CACHE[category][path]
    except KeyError:
        pass


def setup(size: int=MAX_SIZE, default: str=None) -> None:
    """Creates cache with custom size and default category key"""
    global DEFAULT_CATEGORY
    global MAX_SIZE

    if CACHE:
        raise CacheError("Cache already contains data! "
            "Flush cache before attempting to make changes.")

    if size:
        if not isinstance(size, int):
            raise TypeError("Category size must be an integer!")
        if size > 0:
            MAX_SIZE = size

    if default:
        try:
            hash(default)
        except TypeError:
            raise TypeError("Default category key must be hashable")
        DEFAULT_CATEGORY = default
    
    flush_cache()

def flush_cache() -> None:
    """Flushes cache and creates new cache using default category
    and size settings."""
    _do_create_cache()

def _do_create_cache() -> None:
    global CACHE
    CACHE = defaultdict(OrderedDict)
