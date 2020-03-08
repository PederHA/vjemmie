from typing import List, Optional

import vjemmie
from discord.ext.commands import Cog

from mycogs import cogs # Define custom cogs in your own module
import botsecrets # Pass entire botsecrets module to vjemmie.run


def main(secrets, cogs: Optional[List[Cog]]=None) -> None:       
    vjemmie.run(secrets, cogs)


if __name__ == "__main__":
    main(botsecrets, cogs)
