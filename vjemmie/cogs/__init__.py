"""
Add/remove bot cogs in this module.
"""
from discord.ext import commands

from .admin_cog import *
from .autochess_cog import *
from .avatar_cog import *

from .experimental_cog import *
from .fun_cog import *
from .image_cog import *
from .meme_cog import *
from .pubg_cog import *
from .reddit_cog import *
from .sound_cog import *
from .stats_cog import *
from .twitter_cog import *
from .user_cog import *
from .weather_cog import *
from .wowprogress_cog import *


COGS = [
        v for k, v in dict(locals()).items()
        if k.endswith("Cog") and issubclass(v, commands.Cog)
    ]

from .botsetup_cog import BotSetupCog
