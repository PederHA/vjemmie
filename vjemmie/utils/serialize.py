import json
from typing import Any, Union
from pathlib import Path


def create_json_file(filepath: Union[str, Path], default_factory: Union[list, dict]=dict, encoding="utf-8", **kwargs) -> None:
    try:
        filepath = Path(filepath)
    except:
        raise TypeError("file path must be a path-like object!")
    
    # Make sure file has correct suffix
    if not filepath.suffix.lower() == ".json":
        filepath = filepath.with_name(f"{filepath.name}.json")

    # NOTE: Should this be included?
    #if not filepath.exists():
    #    filepath.touch()

    with open(filepath, "w", encoding=encoding, **kwargs) as f:
        f.write(default_factory)


def load_json(fp: str, default_factory: Union[list, dict]) -> Union[list, dict]:
    """Not sure wtf this is. Use `utils.get_cached` instead"""
    f = open(fp, "r")
    try:
        data =  json.load(f)
        f.close()
        return data
    except json.decoder.JSONDecodeError:
        contents = f.read()
        f.close()
        new_fp = f"{fp.split('.', 1)[0]}_damaged.txt"
        with open(new_fp, "w") as df:
            print(
            f"{fp} is damaged!\n"
            f"Saving old file as {new_fp} and creating blank {fp}.\n"
            "Manual correction of errors in original file must be performed before "
            "attempting to use it again!"
            )
            df.write(contents)
        f = open(fp, "w")
        f.write(f"{default_factory()}")
        f.close()
        return default_factory()


def dump_json(fp: str, obj: Any, default: Any=None) -> None:
    d = json.dumps(obj, indent=4, default=default)
    with open(fp, "w") as f:
        f.write(d)