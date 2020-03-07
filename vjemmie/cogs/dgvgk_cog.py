import socket

import discord
from discord.ext import commands
import mcstatus

from .base_cog import BaseCog
from ..utils.converters import IPAddressConverter
from ..utils.exceptions import CommandError
from ..utils.serialize import dump_json
from ..utils.caching import get_cached

CONF = "DGVGK/minecraft.json"

class DGVGKCog(BaseCog):
    """De Gode Venners Gamingkrok commands."""
    
    SERVER_IP = "35.228.88.187"
    SERVER_PORT = 25565

    FILES = [CONF]

    def __init__(self) -> None:
        self._set_ip_port()

    def _set_ip_port(self) -> None:


    async def _get_server_status(self) -> mcstatus.pinger.PingResponse:
        try:
            server = mcstatus.MinecraftServer(self.SERVER_IP, self.SERVER_PORT)
            status = server.status()
        except socket.gaierror:
            raise CommandError("Unable to connect to server")
        else:
            return status

    @commands.group(name="mc")
    async def mc(self, ctx: commands.Context) -> None:
        pass

    @mc.command(name="ip")
    async def set_server_ip(self, ctx: commands.Context, ip: IPAddressConverter) -> None:
        self.SERVER_IP = str(ip)
        await ctx.send(f"Minecraft server IP set to `{self.SERVER_IP}`")

    @mc.command(name="port")
    async def set_server_port(self, ctx: commands.Context, port: int) -> None:
        port = abs(port)
        if port == 0 or port > 65535:
            raise CommandError("Port number must be between 1 and 65535")
        self.SERVER_PORT = port
        await ctx.send(f"Minecraft server port set to `{self.SERVER_PORT}`")

    @mc.command(name="players")
    async def view_players(self, ctx: commands.Context) -> None:
        status = await self._get_server_status()
        players = "\n".join([player.name for player in status.players.sample])
        await self.send_embed_message(ctx, title="Players Online", description=players)