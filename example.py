from typing import List

from vjemmie import run
from discord.ext.commands import Cog

from mycogs import cogs # Define custom cogs in your own module
import botsecrets


def main(secrets, cogs: List[Cog]) -> None:       
    run(secrets, cogs)


if __name__ == "__main__":
    main(botsecrets, cogs)
