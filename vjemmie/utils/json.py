import json
from typing import Any, Union
from pathlib import Path

from aiofile import AIOFile

from .wsl import in_wsl


async def dump_json(fp: str, obj: Any, default: Any=None) -> None:
    d = json.dumps(obj, indent=4, default=default)
    async with AIOFile(fp, "w") as f:
        await f.write(d)


def dump_json_blocking(fp: str, obj: Any, default: Any=None) -> None:
    """Blocking fallback."""
    d = json.dumps(obj, indent=4, default=default)
    with open(fp, "w") as f:
        f.write(d)


if in_wsl():
    # AIOFile doesn't seem to work on Microsoft's 4.4.0-18362 Linux kernel
    # Warning received on startup: <frozen importlib._bootstrap>:219: RuntimeWarning: Linux supports fsync/fdsync with io_submit since 4.18 but current kernel 4.4.0-18362-Microsoft doesn't support it. Related calls will have no effect.
    async def blocking_dump(fp: str, obj: Any, default: Any=None) -> None:
        return dump_json_blocking(fp, obj, default)
    dump_json = blocking_dump
