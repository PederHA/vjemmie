import time
from datetime import datetime
from functools import partial

import discord
import requests
import websockets
from aiohttp import web
from discord.ext import commands
from websockets.server import WebSocketServerProtocol

from .base_cog import BaseCog
from ..utils.checks import owners_only
from ..utils.exceptions import CommandError
from ..utils.experimental import get_ctx


class ExperimentalCog(BaseCog):
    """Unstable/bad/temporary commands"""

    EMOJI = ":robot:"
    def __init__(self, bot) -> None:
        super().__init__(bot)
        #self.bot.loop.run_until_complete(websockets.serve(self.handler, "localhost", 9002))

    @commands.command(name="dbg")
    @owners_only()
    async def dbg(self, ctx: commands.Context) -> None:
        """Drop into debugger for TestingCog."""
        breakpoint()
        print("yeah!")

    async def handler(self, websocket: WebSocketServerProtocol, path: str):
        cmd = await websocket.recv()

        # Is this really the way to get a cmd invocation ctx for a given channel?
        channel = self.bot.get_channel(560503336013529091)
        command = self.bot.get_command(cmd)
        ctx = await self.bot.get_context(await channel.fetch_message(channel.last_message_id))
        
        await ctx.invoke(command)
        
        await websocket.send("OK")
