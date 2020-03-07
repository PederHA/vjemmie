import sys
from contextlib import suppress
from typing import List

with suppress(ImportError):
    import uvloop # poetry run pip install (wheel) uvloop
    uvloop.install()

from discord.ext.commands import Bot, Command, Cog

from .cogs import COGS, BotSetupCog
from .tests.test_cog import TestCog
from .utils.patching.commands import patch_command_signature


patch_command_signature(Command)


def run(
    secrets,
    cogs: List[Cog] = None,
    test: bool = False,
    command_prefix: str="!",
    description: str="VJ Emmie",
    pm_help: bool=False,
    **kwargs
) -> None:
    # Setup cogs
    if not cogs:
        cogs = []
    if test:
        cogs.append(TestCog)
    cogs = cogs + COGS  # add default cogs

    # Bot setup
    bot = Bot(
        command_prefix=command_prefix, 
        description=description,
        pm_help=pm_help, 
        **kwargs
    )
    setattr(bot, "secrets", secrets)  # add secrets module as bot attribute

    # Add cogs
    for cog in cogs:
        bot.add_cog(cog(bot=bot))
    bot.add_cog(BotSetupCog(bot=bot))  # make sure BotSetupCog runs last

    # Run bot
    bot.run(secrets.BOT_TOKEN if not test else secrets.DEV_BOT_TOKEN)
