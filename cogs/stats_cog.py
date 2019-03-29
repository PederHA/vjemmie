from discord.ext import commands
import discord
from cogs.base_cog import BaseCog


class StatsCog(BaseCog):
    def __init__(self, bot: commands.Bot) -> None: