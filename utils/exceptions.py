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

class BotPermissionError(Exception):
    """Bot lacks permissions to perform action"""

class FatalBotException(Exception):
    pass

#__all__ = [
#    "WordExceededLimit", "NonImgUrlError", "InvalidURLError", 
#    "EmptyArgsError", "NoContextException", "CategoryError",
#    "CommandError", "CogError", "FileTypeError", "FileSizeError",
#    "BotPermissionError", "FatalBotException"
#]

VJEMMIE_EXCEPTIONS = [
    v for k, v in dict(locals()).items()
    #if k in __all__ and issubclass(v, Exception)
    if hasattr(v, "__bases__") and Exception in v.__bases__
]
