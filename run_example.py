from contextlib import suppress
from typing import List, Optional

from discord.ext.commands import Cog
import vjemmie

import botsecrets # Pass entire botsecrets module to vjemmie.run

try:
    from mycogs import cogs # Define custom cogs in your own module
except ImportError:
    cogs = []


def main(secrets, cogs: Optional[List[Cog]]=None) -> None:       
    vjemmie.run(secrets, cogs)


if __name__ == "__main__":
    main(botsecrets, cogs)
