from pathlib import Path
from typing import Union
from os import PathLike


def rename_file(filepath: Union[bytes, str, Path, PathLike], new_name: str) -> None:
    p = Path(filepath)  
    orig_suffix = p.suffix
    p = p.with_name(new_name)
    if not p.suffix and orig_suffix:
        p = p.with_name(f"{p.name}{orig_suffix}")
    return str(p)

new = rename_file("myfile.json", "otherfile")
