import discord
from discord.ext import commands
from bo4api import get_player
import traceback

class CodCog:
    def __init__(self, bot: commands.Bot, log_channel_id: int=None) -> None:
        self.bot = bot
        self.log_channel_id = log_channel_id

    @commands.command(name="cod")
    async def codstats(self, ctx: commands.Context, battletag: str, time_filter: str=None) -> None:
        if time_filter in ["weekly", "week"]:
            weekly = True
        elif time_filter is None:
            weekly = False
        else:
            await ctx.send(f'Invalid optional time argument **{weekly}**. Use **week** for weekly stats.')
            raise Exception
        
        try:
            stats = get_player(battletag, weekly=weekly)
        except:
            await ctx.send("Something went wrong. Make sure the provided battletag exists and is in the format **<Name>#<Tag>** (optional: week).")
        else:
            await ctx.send(f"```{stats}```")