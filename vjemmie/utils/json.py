import json
from typing import Any, Union
from pathlib import Path

from aiofile import AIOFile


async def dump_json(fp: str, obj: Any, default: Any=None) -> None:
    d = json.dumps(obj, indent=4, default=default)
    async with AIOFile(fp, "w") as f:
        await f.write(d)