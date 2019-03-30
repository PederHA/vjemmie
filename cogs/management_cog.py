from discord.ext import commands
import discord
from cogs.base_cog import BaseCog
from datetime import datetime
from time import perf_counter, time
import asyncio
from collections import defaultdict
import json
from cogs.sound_cog import AudioPlayer

class DateTimeEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime):
            return o.isoformat()
        return super().default(o)

class ManagementCog(BaseCog):
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
        if player.current:
            current_title = player.current.title
            current_source = player.current.web_url if player.current.web_url else "Local file"
        else:
            current_title = None
            current_source = None
        p_data["current"] = current_title
        p_data["source"] = current_source

        return p_data