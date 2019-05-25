import json
import os
import time
from typing import Any, Dict, Union
from collections import deque, defaultdict
from functools import partial

from recordclass import recordclass
from recordclass.recordobject import recordclasstype


_deque = partial(deque, [], maxlen=5)
CACHE = defaultdict(_deque)
CachedContent = recordclass("CachedContent", "contents content_type modified")


def get_cached(path: str, category: str) -> Union[str, dict]:
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
