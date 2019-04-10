import asyncio
import json
from collections import defaultdict
from datetime import datetime, timedelta
from time import perf_counter, time

import discord
from discord.ext import commands

from cogs.base_cog import BaseCog
from cogs.sound_cog import AudioPlayer
from ext.checks import admins_only, disabled_cmd


class DateTimeEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime):
            return o.isoformat()
        return super().default(o)

class ManagementCog(BaseCog):
    """Commands and methods used to manage non-guild related bot functionality."""
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__(bot)
        self.START_TIME = datetime.now()
        self.bot.loop.create_task(self.monitor_players())

    async def monitor_players(self) -> None:
        sound_cog = self.bot.get_cog("SoundCog")
        players = sound_cog.players
        
        while True:
            out_players = defaultdict(dict)
            for gid, player in players.items():
                if not player:
                    continue
                out_players[gid] = await self._get_player_data(gid, player)    
            with open("out/audioplayers.json", "w") as f:
                json.dump(out_players, f, indent=4, cls=DateTimeEncoder)
            await asyncio.sleep(60)
        
    async def _get_player_data(self, gid: int, player: AudioPlayer) -> dict:
        """Creates dictionary from specific AudioPlayer instance attributes"""
        p_data = {}

        p_data["guild_name"] = str(self.bot.get_guild(gid))
        p_data["created_at"] = player.created_at
        p_data["current"] = player.current.web_url or "Local file" if player.current else None
        p_data["source"] = player.current.title if player.current else None

        return p_data
    
    async def monitor_aiohttp_sessions(self) -> None:
        while True:
            await asyncio.sleep(60)
            
            if not hasattr(self.bot, "sessions"):
                continue

    @commands.command(name="reacts")
    @admins_only()
    @disabled_cmd()    
    async def react_messages(self, ctx) -> None:
        #while True:
        last_hour = datetime.now() - timedelta(hours=2) # Some timezone fuckery means we have to do 2 here

        for guild in self.bot.guilds:
            for channel in guild.text_channels:
                async for msg in channel.history(after=last_hour):
                    if msg.reactions:
                        reactions = [reaction for reaction in msg.reactions if reaction.count>1]
                        if len(reactions)>=3:
                            for reaction in reactions:
                                await msg.add_reaction(reaction.emoji)

        #after = datetime.now() - timedelta(hours=24)
        #channel = self.bot.get_channel(133332608296681472)
        #async for msg in channel.history(limit=500, after=after):
        #    if msg.reactions:
        #        reactions = [reaction for reaction in msg.reactions if reaction.count>1]
        #        if len(reactions)>=3:
        #            for reaction in reactions:
        #                await msg.add_reaction(reaction.emoji)

