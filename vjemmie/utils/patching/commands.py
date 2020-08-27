from discord.ext.commands import converter as converters
from discord.ext.commands import Command

@property
def signature(self):
    """Returns a POSIX-like signature useful for help command output."""
    if self.usage is not None:
        return self.usage

    params = self.clean_params
    if not params:
        return ''

    result = []
    for name, param in params.items():
        greedy = isinstance(param.annotation, converters._Greedy)
        
        # OUR PATCH
        # Skip keyword-only parameters
        if param.kind == param.KEYWORD_ONLY:
            continue

        if param.default is not param.empty:
            # We don't want None or '' to trigger the [name=value] case and instead it should
            # do [name] since [name=None] or [name=] are not exactly useful for the user.
            should_print = param.default if isinstance(param.default, str) else param.default is not None
            if should_print:
                result.append('[%s=%s]' % (name, param.default) if not greedy else
                                '[%s=%s]...' % (name, param.default))
                continue
            else:
                result.append('[%s]' % name)

        elif param.kind == param.VAR_POSITIONAL:
            result.append('[%s...]' % name)
        elif greedy:
            result.append('[%s]...' % name)
        elif self._is_typing_optional(param.annotation):
            result.append('[%s]' % name)
        else:
            result.append('<%s>' % name)

    return ' '.join(result)

def patch_command_signature(cmd: Command) -> Command:
    """Patches `discord.ext.commands.Command`'s `signature` method to ignore
    keyword-only parameters."""
    cmd.signature = signature
    setattr(cmd, "help_doc", help_doc)

@property
def help_doc(instance) -> str:
    # Only show up to method param list if it exists
    return instance.help.split("\nParameters")[0] if instance.help else ""
