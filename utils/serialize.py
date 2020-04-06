import json
from typing import Any, Union


def load_json(fp: str, default_factory:Union[list, dict]=list, encoding="utf-8") -> Union[list, dict]:
    with open(fp, "r", encoding=encoding) as f:
        try:
            r = json.load(f)
        except json.JSONDecodeError:
            return default_factory()
        else:
            return r

def dump_json(fp: str, obj: Any, default: Any=None, encoding="utf-8") -> None:
    d = json.dumps(obj, indent=4, default=default)
    with open(fp, "w", encoding="utf-8") as f:
        f.write(d)