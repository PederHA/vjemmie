"""
Add/remove bot cogs in this module.
"""

from contextlib import suppress

from discord.ext import commands

from cogs.admin_cog import AdminCog
from cogs.avatar_cog import AvatarCog
from cogs.experimental_cog import ExperimentalCog
from cogs.fun_cog import FunCog
from cogs.image_cog import ImageCog
from cogs.management_cog import ManagementCog
from cogs.meme_cog import MemeCog
from cogs.pubg_cog import PUBGCog
from cogs.reddit_cog import RedditCog
from cogs.sound_cog import SoundCog
from cogs.stats_cog import StatsCog
from cogs.twitter_cog import TwitterCog
from cogs.user_cog import UserCog
from cogs.weather_cog import WeatherCog
from cogs.wowprogress_cog import WoWProgressCog

# Private cogs. You can delete this if you cloned the repo
with suppress(ImportError):
    from cogs.war3_cog import War3Cog
    from cogs.pfm_cog import PFMCog    


# List of all cogs in the local namespace
# This should be imported in the bot's main module
COGS = [
    v for k, v in dict(locals()).items()
    if k.endswith("Cog") and issubclass(v, commands.Cog)
]
