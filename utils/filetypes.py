from typing import Union, BinaryIO

import magic

T = Union[BinaryIO, bytes]

BUFSIZE = 1024

def _get_file_mimetype(file_: T, bufsize: int) -> str:
    if hasattr(file_, "read"):
        pos = file_.tell()
        if pos != 0:
            file_.seek(0)
        b = file_.read(bufsize)
        file_.seek(pos)
    else:
        b = file_
    return magic.from_buffer(b, mime=True)


def check_file_audio(file_: T, bufsize: int=BUFSIZE) -> bool:
    return _get_file_mimetype(file_, bufsize).startswith("audio/")


def check_file_video(file_: T, bufsize: int=BUFSIZE) -> bool:
    return _get_file_mimetype(file_, bufsize).startswith("video/")


def check_file_image(file_: T, bufsize: int=BUFSIZE) -> bool:
    return _get_file_mimetype(file_, bufsize).startswith("image/")


def get_file_mimetype(file_: T, bufsize: int=BUFSIZE) -> str:
    return _get_file_mimetype(file_, bufsize)
