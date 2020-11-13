from datetime import datetime, timedelta
from collections import defaultdict
from typing import DefaultDict, Dict, List, Optional, Tuple
import asyncio
from dataclasses import dataclass, field

import discord
from discord.ext import commands
from discord.ext import tasks
from discord.utils import get

from .base_cog import BaseCog
from ..utils.exceptions import CommandError
from ..db import get_db, DatabaseConnection
from ..config import MAIN_DB

BRONJAM_INTERVAL = 24000 # seconds
BRONJAM_ALERT_ADVANCE = 10 * 60
BRONJAM_SCHEDULE = {}
SCHEDULE: DefaultDict[int, List[datetime]] = defaultdict(list) # day of month : list of bronjam spawns that day



def create_schedule():
    d = datetime(year=2020, month=11, day=13, hour=15, minute=00)
    while d.month == 11:
        if d.month != 11:
            break
        SCHEDULE[d.day].append(d - timedelta(seconds=BRONJAM_ALERT_ADVANCE))
        d += timedelta(seconds=BRONJAM_INTERVAL)


@dataclass
class BagGuild:
    bot: commands.Bot
    guild: discord.Guild
    channel: discord.TextChannel
    role: discord.Role

    async def alert(self) -> None:
        await self.channel.send(f"B A G in {BRONJAM_ALERT_ADVANCE//3600} minutes!")

    async def add_member(self, member: discord.Member) -> None:
        if self.role in member.roles:
            raise CommandError(f"You already have the {self.role.name} role!")
        await member.add_roles(self.role)

    async def remove_member(self, member: discord.Member) -> None:
        if self.role in member.roles:
            raise CommandError(f"You do not have the {self.role.name} role!")
        await member.remove_roles(self.role)

    def _dump(self) -> Tuple[int, int, int]:
        return (self.guild.id, self.channel.id, self.role.id)

    @classmethod
    def from_ids(cls, 
        bot: commands.Bot, 
        guild_id: int, 
        channel_id: int, 
        role_id: int
    ) -> object:
        """Creates a new BagGuild from Discord IDs.
        NOTE
        ----
        Will fail on retrieving role if `bot.get_guild(...)` returns `None`.
        """
        obj = cls.__new__(cls)
        obj.bot = bot
        obj.guild = bot.get_guild(guild_id)
        obj.channel = bot.get_channel(channel_id)
        obj.role = get(obj.guild.roles, id=role_id)
        return obj


@dataclass
class Bags:
    bot: commands.Bot
    db: DatabaseConnection
    _guilds: Dict[int, BagGuild] = field(default_factory=dict)

    async def alert_guilds(self) -> None:
        for guild in self._guilds.values():
            await guild.alert()

    async def add_guild(self, ctx: commands.Context, channel: discord.TextChannel, role: discord.Role) -> None:
        if ctx.guild.id in self._guilds:
            raise CommandError("This Discord server has already been configured for bag alerts!")
        guild = BagGuild(
            bot=self.bot,
            guild=ctx.guild,
            channel=channel,
            role=role
        )
        self._guilds[ctx.guild.id] = guild
        await self.db.bag_add_guild(*(guild._dump()))

    async def get_guild(self, ctx: commands.Context) -> BagGuild:
        if not ctx.guild:
            raise CommandError("This command is not supported in DMs!")
        g = self._guilds.get(ctx.guild.id)
        if not g:
            raise CommandError(
        "This server has not been configured for bag alerts yet. "
        f"Run `{self.bot.command_prefix}bag setup` to get started."
        )

    async def _restore_from_db(self) -> None:
        guilds = await self.db.bag_get_guilds()
        if not guilds:
            return
        for guild in guilds:
            # TODO: Wrap this in a try..except
            self._guilds[guild[0]] = BagGuild.from_ids(self.bot, *guild)


class WowCog(BaseCog):
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__(bot)
        create_schedule()
        self.bag_guilds = Bags(self.bot, get_db(MAIN_DB))

        # Timer synchronization variables
        self.bag_synced = False
        self.syncing = None

        # Start alert loop     
        self.bag_alert.start()
        
    @commands.Cog.listener()
    async def on_ready(self) -> None:
        await self.bag_guilds._restore_from_db()

    @tasks.loop(seconds=BRONJAM_INTERVAL)
    async def bag_alert(self) -> None:
        while not self.bag_synced:
            if not self.syncing:
                self.syncing = self.bot.loop.create_task(self._bag_alert_synchronize())
            await asyncio.sleep(1) # this is super primitive
        await self.bag_guilds.alert_guilds()

    async def _bag_alert_synchronize(self) -> None:
        """terrible method for syncing bronjam spawn timer with loop"""
        if not self.bag_synced:
            now = datetime.now()
            spawns = SCHEDULE[now.day]
            for spawn in spawns:
                if now > spawn:
                    continue       
                wait = (spawn - now).total_seconds()
                await asyncio.sleep(wait)
                self.bag_synced = True
                    
    @commands.group(name="bag")
    async def bag(self, ctx: commands.Context) -> None:
        if not ctx.invoked_subcommand:
            await ctx.invoke(self.bot.get_command("help"), "bag")

    @bag.command(name="setup")
    async def bag_setup(
        self, 
        ctx: commands.Context, 
        channel: commands.TextChannelConverter=None, 
        role: commands.RoleConverter=None
    ) -> None:
    # TODO: make sure role is mentionable
        if not channel or not role:
            return await ctx.send(f"Usage: `{self.bot.command_prefix}bag setup <text channel name> <role name>`")
        await self.bag_guilds.add_guild(ctx, channel, role)   
        await ctx.send(
            "Guild has been configured for bag alerts. "
            f"Members can now type `{self.bot.command_prefix}bag add` & `{self.bot.command_prefix}bag remove`"
            "To enable bag alerts."
        ) 

    @bag.command(name="add", aliases=["me"])
    async def bag_add(self, ctx: commands.Context) -> None:
        guild = await self.bag_guilds.get_guild(ctx)
        await guild.add_member(ctx.message.author)
        await ctx.send(f"Added the `{guild.role.name}` role!")

    @bag.command(name="remove", aliases=["stop"])
    async def bag_remove(self, ctx: commands.Context) -> None:
        guild = await self.bag_guilds.get_guild(ctx)
        await guild.remove_member(ctx.message.author)
        await ctx.send(f"Removed the `{guild.role.name}` role!")