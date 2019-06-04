import json
import os
import time
from typing import Any, Dict, Union
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

def get_cached(path: str, category: str=None, timestamp: bool=False) -> Union[str, dict]:
    if not CACHE:
        _do_create_cache()
    
    if not category:
        category = DEFAULT_CATEGORY

    cached = _get_from_cache(path, category)
    
    if cached:
        last_modified = cached.modified
    
    modified = os.path.getmtime(path)

    if not cached or last_modified != modified:
        extension = os.path.splitext(path)[1]
        is_json = extension == ".json"
        cache_data = _get_file_contents(path, category, is_json)
        _add_to_cache(path, category, cache_data)
        contents = cache_data.contents
    else:
        contents = cached.contents
    
    # Make tuple of contents and modification timestamp if param timestamp==True
    if timestamp:
        contents = (contents, modified)

    return contents


def _get_file_contents(path: str, category: str, is_json: bool) -> CachedContent:
    with open(path, "r") as f:
        if is_json:
            contents = json.load(f)
        else:
            contents = f.read()
    modified = os.path.getmtime(path)
    content_type = "json" if is_json else "text"
    return CachedContent(contents, content_type, modified)


def _add_to_cache(path: str, category: str, contents: CachedContent) -> None:
    try:
        del CACHE[category][path]
    except KeyError:
        pass
    if len(CACHE[category]) == MAX_SIZE:
        CACHE[category].popitem(last=False) # Pop oldest item
    CACHE[category][path] = contents


def _get_from_cache(path: str, category: str) -> CachedContent:
    try:
        return CACHE[category][path]
    except KeyError:
        pass


def setup_cache(category_size: int=MAX_SIZE, default_category: str=None) -> None:
    global DEFAULT_CATEGORY
    global MAX_SIZE

    if CACHE:
        raise CacheError("Cache already contains data! "
            "Flush cache before attempting to make changes.")
    
    if category_size:
        try:
            category_size = int(category_size)
        except:
            raise TypeError("Category size must be an integer!")
        if category_size > 0:
            MAX_SIZE = category_size

    if default_category:
        if not isinstance(default_category, str):
            raise TypeError("Default category name must be a string!")
        DEFAULT_CATEGORY = default_category
    
    _do_create_cache()

def flush_cache() -> None:
    _do_create_cache()

def _do_create_cache() -> None:
    global CACHE
    CACHE = defaultdict(OrderedDict)
