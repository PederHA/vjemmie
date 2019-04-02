"""
Add/remove cogs in this module.

NOTE
----
Only subclasses of discord.ext.commands.Cog are added to __all__!
"""
from discord.ext import commands

from cogs.admin_cog import AdminCog
from cogs.fun_cog import FunCog
from cogs.pfm_memes_cog import PFMCog
from cogs.pubg_cog import PUBGCog
from cogs.reddit_cog import RedditCog
from cogs.user_cog import UserCog
from cogs.wowprogress_cog import WoWProgressCog
from cogs.testing_cog import TestingCog
from cogs.frying_cog import FryingCog
from cogs.weather_cog import WeatherCog
from cogs.war3_cog import War3Cog
from cogs.image_cog import ImageCog
from cogs.sound_cog import SoundCog
from cogs.meme_cog import MemeCog
from cogs.stats_cog import StatsCog
from cogs.management_cog import ManagementCog


__all__ = [
    k for k, v in dict(locals()).items()
    if k.endswith("Cog") and issubclass(v, commands.Cog)
]
