import asyncio
import json
from collections import defaultdict
from datetime import datetime, timedelta
from time import perf_counter, time
from typing import Tuple, List
from functools import partial
from pathlib import Path

import discord
from discord.ext import commands
import boto3

from botsecrets import EC2_INSTANCE_ID
from cogs.base_cog import BaseCog, EmbedField
from cogs.sound_cog import AudioPlayer
from utils.checks import admins_only, disabled_cmd
from utils.converters import BoolConverter
from utils.exceptions import CommandError
from utils.serialize import dump_json
from itertools import chain

class DateTimeEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime):
            return o.isoformat()
        return super().default(o)

class ManagementCog(BaseCog):
    DISABLE_HELP = True
    
    FILES = [
        "out/audioplayers.json",
    ]
    
    DIRS = [
        "out"
    ]

    """Commands and methods used to manage non-guild related bot functionality."""
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__(bot)
        self.bot_ec2 = boto3.resource("ec2").Instance(EC2_INSTANCE_ID)

    @commands.command(name="reacts")
    @admins_only()
    @disabled_cmd()    
    async def react_messages(self, ctx) -> None:
        last_hour = datetime.now() - timedelta(hours=2) # Some timezone fuckery means we have to do 2 here

        for guild in self.bot.guilds:
            for channel in guild.text_channels:
                async for msg in channel.history(after=last_hour):
                    if msg.reactions:
                        reactions = [reaction for reaction in msg.reactions if reaction.count>1]
                        if len(reactions)>=3:
                            for reaction in reactions:
                                await msg.add_reaction(reaction.emoji)
    
    @commands.command(name="cogs", aliases=["get_cogs"])
    @admins_only() 
    async def get_cogs_status(self, ctx) -> None:
        """Not sure why I made this but w/e. Might be useful."""
        # Get cogs help status
        enabled, disabled = await self._get_cogs_by_help_status()

        # Send message
        e_out = "**Enabled:**\n" + "\n".join(enabled)
        d_out = "**Disabled:**\n" + "\n".join(disabled)
        out = f"{e_out}\n\n{d_out}"  
        await self.send_text_message(out, ctx)

        # Log cog help status to drive
        to_run = partial(self._dump_cogs, enabled, disabled)
        await self.bot.loop.run_in_executor(None, to_run)

    async def _get_cogs_by_help_status(self) -> Tuple[list, list]:   
        enabled = []
        disabled = []
        
        for cog in await self.get_cogs(all_cogs=True):
            l = disabled if cog.DISABLE_HELP else enabled
            l.append(cog.cog_name)
        
        return enabled, disabled

    def _dump_cogs(self, enabled, disabled) -> None:
        out_dict = {
                "enabled": enabled,
                "disabled": disabled
                }
        dump_json("db/cogs.json", out_dict)

    @commands.command(name="fs")
    async def get_dirs_files(self, ctx: commands.Context) -> None:
        # Get all cogs
        cogs = await self.get_cogs(all_cogs=True)
        
        # Get lists of files and directories belonging to each cog
        dirs = list(chain.from_iterable([cog.DIRS for cog in cogs if cog.DIRS]))
        files = list(chain.from_iterable([cog.FILES for cog in cogs if cog.FILES]))
        
        # Make embed fields for files and directories
        f_field = EmbedField(name="Files", value="\n".join(files))
        d_field = EmbedField(name="Directories", value="\n".join(dirs))
        
        embed = await self.get_embed(ctx, fields=[f_field, d_field])
        await ctx.send(embed=embed)
    
    @commands.command(name="ip")
    @admins_only()
    async def ip(self, ctx: commands.Context,  *, ipv6: BoolConverter(["ipv6"])=False) -> None:
        """Displays bot's public EC2 IPv4/6 address"""  
        # Fetch IP non-blocking
        to_run = partial(self.get_ec2_ip, ipv6=ipv6)
        ip_address = await self.bot.loop.run_in_executor(None, to_run)
        
        v = "6" if ipv6 else "4"
        await ctx.send(f"Public IPv{v} address: {ip_address}")
    
    def get_ec2_ip(self, ipv6: bool=False) -> str:
        """
        Fetches public IPv4 or IPv6 address of EC2 instance bot is running on.

        IMPORTANT NOTE
        --------------
        AWS credentials must be configured through the AWS CLI before this
        command can be used.
        """
        if ipv6:
            iface = self.bot_ec2.network_interfaces[0]
            try:
                ip_address = iface.ipv6_addresses[0]
            except IndexError:
                raise AttributeError("Bot's EC2 instance has no associated IPv6 addresses!")
        else:
            ip_address = self.bot_ec2.public_ip_address
        
        return ip_address
