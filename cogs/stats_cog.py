from discord.ext import commands
import discord
from cogs.base_cog import BaseCog
from datetime import datetime


class StatsCog(BaseCog):
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__(bot)
        self.START_TIME = datetime.now()

    @commands.command(name="uptime")
    async def bot_uptime(self, ctx: commands.Context) -> None:
        up = datetime.now() - self.START_TIME
        days = up.days
        hours, remainder = divmod(up.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        # If you want to take into account fractions of a second
        seconds += round(up.microseconds / 1e6)
        
        # Returns empty string if number is 0
        up_fmt = lambda dur, unit: f"{dur}{unit} " if dur else ""

        await ctx.send("Bot has been up for " 
                       f"{up_fmt(days, 'd')}"
                       f"{up_fmt(hours, 'h')}"
                       f"{up_fmt(minutes, 'm')}"
                       f"{up_fmt(seconds, 's')}")