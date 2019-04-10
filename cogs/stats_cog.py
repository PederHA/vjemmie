from discord.ext import commands
import discord
from cogs.base_cog import BaseCog
from datetime import datetime
from time import perf_counter, time
import json
from ext.checks import owners_only


class StatsCog(BaseCog):
    """Commands and methods for gathering bot statistics."""

    EMOJI = ":chart_with_upwards_trend:"

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

    @commands.command(name="get_players")
    @owners_only()
    async def get_players(self, ctx) -> None:
        sound_cog = self.bot.get_cog("SoundCog")
        players = sound_cog.players
        #with open("out/audioplayers.json", "r") as f:
        #    players = json.load(f)
        
        out = []
        for gid, player in players.items():
            #embed_body = ( 
            #        f"**Created at**: {player['created_at']}\n"
            #        f"**Currently playing**: {player['current']}"
            #        f"**Guild ID**: {gid}\n"
            #        )
            embed_body = ( 
                    f"**Created at**: {player.created_at}\n"
                    f"**Currently playing**: {player.current.title if player.current else None}\n"
                    f"**Guild ID**: {gid}\n"
                    )            
            out.append((str(self.bot.get_guild(gid)), embed_body))

        # Post active players
        if out:
            for gname, o in out:
                await self.send_embed_message(ctx, gname, o, footer=False)
        else:
            await ctx.send("No active audio players")