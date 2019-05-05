class WordExceededLimit(Exception):
    pass

class NonImgURL(Exception):
    pass

class InvalidURL(Exception):
    pass

class EmptyArgsError(Exception):
    pass

class InvalidObjectType(Exception):
    pass

class NoContextException(Exception):
    """Raised if bot cannot retrieve context from call stack."""
    pass