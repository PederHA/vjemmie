import json
from typing import Any


def load_json(self, fp: str, default=list) -> list:
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
        f.write(f"{default()}")
        f.close()
        return default()

def dump_json(self, fp: str, obj: Any) -> None:
    with open(fp, "w") as f:
        json.dump(obj, f, indent=4)