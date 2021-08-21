import sys
from contextlib import suppress
from typing import List, Optional

from discord.ext.commands import Cog
from loguru import logger

import vjemmie

try:
    from mycogs import cogs  # Define custom cogs in your own module
except ImportError:
    cogs = []


def main(cogs: Optional[List[Cog]] = None, **kwargs) -> None:
    vjemmie.run(cogs, **kwargs)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        main(cogs)
    else:
        logger.info("Dev Mode Active")
        main(cogs, test=True, command_prefix="?")
