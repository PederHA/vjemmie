from typing import Union, BinaryIO

import magic

T = Union[BinaryIO, bytes]

def _get_file_mimetype(file_: T, bufsize: int) -> str:
    if hasattr(file_, "read"):
        b = file_.read(bufsize)
    else:
        b = file_
    return magic.from_buffer(b, mime=True)

def check_file_audio(file_: T, bufsize: int=1024) -> bool:
    return _get_file_mimetype(file_, bufsize).startswith("audio/")

def check_file_video(file_: T, bufsize: int=1024) -> bool:
    return _get_file_mimetype(file_, bufsize).startswith("video/")


