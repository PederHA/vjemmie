import discord
from discord.ext import commands
from bo4api import get_player
from cogs.base_cog import BaseCog

class CodCog(BaseCog):
    @commands.command(name="cod")
    async def codstats(self, ctx: commands.Context, battletag: str, time_filter: str=None) -> None:
        if time_filter in ["weekly", "week"]:
            weekly = True
        elif time_filter is None or time_filter in ["lifetime", "all"]:
            weekly = False
        else:
            raise discord.DiscordException(f'Invalid time argument "**{time_filter}**". Type `!cod <btag> week` for weekly stats.')
        
        try:
            stats = get_player(battletag, weekly=weekly)
        except:
            await ctx.send("Something went wrong. Make sure the provided battletag exists and is in the format **<Name>#<Tag>** (optional: week).")
        else:
            await ctx.send(f"```{stats}```")