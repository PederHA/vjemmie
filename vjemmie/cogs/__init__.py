"""
Add/remove bot cogs in this module.
"""
from contextlib import suppress

from discord.ext import commands

from .admin_cog import AdminCog
from .autochess_cog import AutoChessCog
from .avatar_cog import AvatarCog
from .experimental_cog import ExperimentalCog
from .fun_cog import FunCog
from .image_cog import ImageCog
from .management_cog import ManagementCog
from .meme_cog import MemeCog
from .pubg_cog import PUBGCog
from .reddit_cog import RedditCog
from .sound_cog import SoundCog
from .stats_cog import StatsCog
from .twitter_cog import TwitterCog
from .user_cog import UserCog
from .weather_cog import WeatherCog
from .wowprogress_cog import WoWProgressCog

with suppress(ImportError):
    from .pfm_cog import PFMCog
    from .dgvgk_cog import DGVGKCog
    
COGS = [
        v for k, v in dict(locals()).items()
        if k.endswith("Cog") and issubclass(v, commands.Cog)
    ]

from .botsetup_cog import BotSetupCog
