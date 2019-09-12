from typing import Union, BinaryIO

import magic

T = Union[BinaryIO, bytes]

BUFSIZE = 1024

def _get_file_mimetype(file: T, bufsize: int) -> str:
    if hasattr(file, "read"):
        pos = file.tell()
        if pos != 0:
            file.seek(0)
        b = file.read(bufsize)
        file.seek(pos)
    else:
        b = file
    return magic.from_buffer(b, mime=True)


def check_file_audio(file: T, bufsize: int=BUFSIZE) -> bool:
    return _get_file_mimetype(file, bufsize).startswith("audio/")


def check_file_video(file: T, bufsize: int=BUFSIZE) -> bool:
    return _get_file_mimetype(file, bufsize).startswith("video/")


def check_file_image(file: T, bufsize: int=BUFSIZE) -> bool:
    return _get_file_mimetype(file, bufsize).startswith("image/")


def get_file_mimetype(file: T, bufsize: int=BUFSIZE) -> str:
    return _get_file_mimetype(file, bufsize)
