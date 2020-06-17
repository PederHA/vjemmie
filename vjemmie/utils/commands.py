from functools import partial
from asyncio import coroutine
from typing import Optional, List, Callable

from discord.ext import commands


def add_command(cog: commands.Cog, 
                coro: Callable, 
                name: str,
                aliases: Optional[List[str]]=None,
                help: Optional[str]=None,
                hidden: bool=False,
                group: Optional[commands.Group]=None,
                checks: Optional[List[Callable]] = None,
                **kwargs
               ) -> None:
    _cmd = coroutine(partial(coro, **kwargs)) # Create partial coro from passed in coro
    
    # These checks seem to be mandatory from Python 3.8 and onwards
    if not hasattr(_cmd, "__module__"):
        _cmd.__module__ = _cmd.func.__module__
    if not hasattr(_cmd, "__globals__"):
        _cmd.__globals__ = _cmd.func.__globals__
    
    if not aliases:
        aliases = []
    if not checks:
        checks = []

    if not help:
        help = ""

    cmd_func = group.command if group else commands.command
    cmd = cmd_func(name=name, aliases=aliases, cog=cog, help=help)(_cmd)
    cmd.cog = cog
    cmd.hidden = hidden
    cmd.checks.extend(checks)
    for param in kwargs: # Remove params from command after passing them in
        cmd.params.pop(param)
    cog.bot.add_command(cmd)