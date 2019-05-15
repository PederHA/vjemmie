class WordExceededLimit(Exception):
    pass

class NonImgUrlError(Exception):
    pass

class InvalidURLError(Exception):
    pass

class EmptyArgsError(Exception):
    pass

class NoContextException(Exception):
    """Raised if bot cannot retrieve context from call stack."""
    pass

class CategoryError(Exception):
    pass

class CommandError(Exception):
    pass

class CogError(Exception):
    pass

class FileTypeError(Exception):
    """Invalid filetype in a given context"""

class FileSizeError(Exception):
    """File Size too small or too large"""

__all__ = [
    "WordExceededLimit", "NonImgUrlError", "InvalidURLError", 
    "EmptyArgsError", "NoContextException", "CategoryError",
    "CommandError", "CogError", "FileTypeError", "FileSizeError",
]

VJEMMIE_EXCEPTIONS = [
    v for k, v in dict(locals()).items()
    if any(k.endswith(_end) for _end in ["Exception", "Error"]) and 
    issubclass(v, Exception)
]
