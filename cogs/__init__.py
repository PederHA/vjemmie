"""
Add/remove bot cogs in this module.
"""

from discord.ext import commands

from cogs.admin_cog import AdminCog
from cogs.fun_cog import FunCog
from cogs.pubg_cog import PUBGCog
from cogs.reddit_cog import RedditCog
from cogs.user_cog import UserCog
from cogs.wowprogress_cog import WoWProgressCog
from cogs.testing_cog import TestingCog
from cogs.frying_cog import FryingCog
from cogs.weather_cog import WeatherCog
from cogs.image_cog import ImageCog
from cogs.sound_cog import SoundCog
from cogs.meme_cog import MemeCog
from cogs.stats_cog import StatsCog
from cogs.management_cog import ManagementCog

# Private cogs. Delete this if you cloned the repo
try:
    from cogs.war3_cog import War3Cog
    from cogs.pfm_cog import PFMCog
except:
    pass

# List of all cogs in the local namespace
# This should be imported in the bot's main module
COGS = [
    v for k, v in dict(locals()).items()
    if k.endswith("Cog") and issubclass(v, commands.Cog)
]
