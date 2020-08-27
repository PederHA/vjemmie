from contextlib import suppress
from typing import List, Optional
import sys

from discord.ext.commands import Cog
import vjemmie

import botsecrets # Pass entire botsecrets module to vjemmie.run

try:
    from mycogs import cogs # Define custom cogs in your own module
except ImportError:
    cogs = []


def main(secrets, cogs: Optional[List[Cog]]=None, **kwargs) -> None:       
    vjemmie.run(secrets, cogs, **kwargs)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        main(botsecrets, cogs)
    else:
        print("Dev Mode Active")
        main(botsecrets, cogs, test=True, command_prefix="?")
