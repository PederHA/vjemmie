from discord.ext import commands

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

class BotException(Exception):
    pass

class FatalBotException(Exception):
    pass

class VoiceConnectionError(commands.CommandError):
    """Custom Exception class for connection errors."""

class InvalidVoiceChannel(VoiceConnectionError):
    """Exception for cases of invalid Voice Channels."""

__all__ = [
    k for k, v in dict(locals()).items()
    if hasattr(v, "__bases__") and Exception in v.__bases__
]
VJEMMIE_EXCEPTIONS = [
    v for k, v in dict(locals()).items()
    #if k in __all__ and issubclass(v, Exception)
    if hasattr(v, "__bases__") and Exception in v.__bases__
]
