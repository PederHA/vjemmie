import sys
from contextlib import suppress
from typing import List, Optional

with suppress(ImportError):
    import uvloop  # poetry run pip install (wheel) uvloop

    uvloop.install()

from discord import Intents
from discord.ext.commands import Bot, Command, Cog

from .cogs import COGS, BotSetupCog
from .tests.test_cog import TestCog
from .utils.patching.commands import patch_command_signature

from .botsecrets import secrets

patch_command_signature(Command)


def get_bot(
    cogs: Optional[List[Cog]] = None,
    test: bool = False,
    command_prefix: str = "!",
    description: str = "VJ Emmie",
    pm_help: bool = False,
    **kwargs
) -> Bot:
    # Setup cogs
    if not cogs:
        cogs = []

    if test:
        cogs.append(TestCog)

    cogs.extend(COGS)  # add default cogs

    # Bot setup
    bot = Bot(
        command_prefix=command_prefix,
        description=description,
        pm_help=pm_help,
        intents=Intents.all(),
        **kwargs
    )

    # Add cogs
    for cog in cogs:
        bot.add_cog(cog(bot=bot))
    bot.add_cog(BotSetupCog(bot=bot))  # make sure BotSetupCog runs last

    return bot


def run(
    cogs: Optional[List[Cog]] = None,
    test: bool = False,
    command_prefix: str = "!",
    description: str = "VJ Emmie",
    pm_help: bool = False,
    **kwargs
) -> None:
    bot = get_bot(cogs, test, command_prefix, description, pm_help, **kwargs)

    # Run bot
    bot.run(secrets.DISCORD_BOT_TOKEN if not test else secrets.DISCORD_DEV_BOT_TOKEN)
