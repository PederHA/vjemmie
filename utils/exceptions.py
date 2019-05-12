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

__all__ = [
    "WordExceededLimit", "NonImgUrlError", "InvalidURLError", 
    "EmptyArgsError", "NoContextException",
    "CategoryError", "CommandError"
]

VJEMMIE_EXCEPTIONS = [
    v for k, v in dict(locals()).items()
    if any(k.endswith(_end) for _end in ["Exception", "Error"]) and 
    issubclass(v, Exception)
]
