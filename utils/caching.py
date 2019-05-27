import json
import os
import time
from typing import Any, Dict, Union
from collections import deque, defaultdict
from functools import partial

from recordclass import recordclass
from recordclass.recordobject import recordclasstype

class CacheError(Exception):
    """Exceptions stemming from operations 
    performed on the cache data structure"""

DEFAULT_CATEGORY = "default"
DEFAULT_SIZE = 5

_deque = partial(deque, [], maxlen=DEFAULT_SIZE)
CACHE = None
CachedContent = recordclass("CachedContent", "contents content_type modified")

def get_cached(path: str, category: str=None) -> Union[str, dict]:
    if not CACHE:
        _do_create_cache()
    
    if not category:
        category = DEFAULT_CATEGORY
    
    extension = os.path.splitext(path)[1]
    is_json = extension == ".json"
    
    cached = _get_from_cache(path, category)
    
    if cached:
        last_modified = cached.modified
        modified = os.path.getmtime(path)

    if not cached or last_modified != modified:
        cache_data = _get_file_contents(path, category, is_json)
        _add_to_cache(path, category, cache_data)
        contents = cache_data.contents
    else:
        contents = cached.contents
    
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
    for cached in CACHE[category]:
        if path in cached:
            CACHE[category].remove(cached)
            break
    CACHE[category].append({path: contents})


def _get_from_cache(path: str, category: str) -> CachedContent:
    if category in CACHE:
        for cached in CACHE[category]:
            if path in cached:
                return cached[path]

def setup_cache(category_size: int=DEFAULT_SIZE, default_category: str=None) -> None:
    global DEFAULT_CATEGORY
    global _deque

    if CACHE:
        raise CacheError("Cache already contains data! "
            "Flush cache before attempting to make changes.")
    
    if category_size:
        try:
            category_size = int(category_size)
        except:
            raise TypeError("Category size must be an integer!")
        _deque.keywords["maxlen"] = category_size

    if default_category:
        if not isinstance(default_category, str):
            raise TypeError("Default category name must be a string!")
        DEFAULT_CATEGORY = default_category
    
    _do_create_cache()

def flush_cache() -> None:
    _do_create_cache()

def _do_create_cache() -> None:
    global CACHE
    CACHE = defaultdict(_deque)    
