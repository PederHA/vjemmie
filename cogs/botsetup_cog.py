import asyncio
from datetime import datetime, timedelta
from typing import Optional, Union

import discord
from discord.ext import commands

from cogs.base_cog import BaseCog, EmbedField
from ext.checks import admins_only, load_blacklist, save_blacklist


class BotSetupCog(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot
        setup()
    
    def setup(self):
        self.bot.sessions = {}
