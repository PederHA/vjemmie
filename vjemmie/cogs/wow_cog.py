import asyncio
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import DefaultDict, Dict, List, Optional, Tuple

import discord
from discord.ext import commands, tasks
from discord.utils import get
from pytz import timezone

from ..config import MAIN_DB
from ..db import DatabaseConnection, get_db
from ..utils.exceptions import CommandError
from ..utils.time import format_time, get_now_time
from .base_cog import BaseCog

BRONJAM_INTERVAL = 12000 # seconds
BRONJAM_ALERT_ADVANCE = 10 * 60
SCHEDULE: DefaultDict[int, List[datetime]] = defaultdict(list) # day of month : list of bronjam spawns that day


def create_schedule():
    d = datetime(year=2020, month=11, day=16, hour=21, minute=30)
    tz = timezone("Europe/Oslo")
    d = tz.localize(d)
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
        await self.channel.send(f"B A G in {BRONJAM_ALERT_ADVANCE//60} minutes! {self.role.mention}")

    async def add_member(self, member: discord.Member) -> None:
        if self.role in member.roles:
            raise CommandError(f"You already have the {self.role.name} role!")
        await member.add_roles(self.role)

    async def remove_member(self, member: discord.Member) -> None:
        if self.role not in member.roles:
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
    """A collection of guilds to ping before Bag spawns."""
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
        guild = self._guilds.get(ctx.guild.id)
        if not guild:
            raise CommandError(
        "This server has not been configured for bag alerts yet. "
        f"Run `{self.bot.command_prefix}bag setup` to get started."
        )
        return guild

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

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        # Start alert loop
        self.bag_alert.start()
        await self.bag_guilds._restore_from_db()

    @tasks.loop(seconds=BRONJAM_INTERVAL)
    async def bag_alert(self) -> None:
        self.bag_synced = False
        syncing = None
        while not self.bag_synced:
            if not syncing:
                syncing = self.bot.loop.create_task(self._bag_alert_synchronize())
            await asyncio.sleep(1) # wait for syncing to complete. this is super primitive
        await self.bag_guilds.alert_guilds()

    async def _bag_alert_synchronize(self) -> None:
        """terrible method for syncing bronjam spawn timer with loop"""
        if not self.bag_synced:
            # Excuse these prints for now :)
            # I need to verify that the loop actually starts
            # on Linux machines
            print("syncing...")
            now = get_now_time()
            spawns = SCHEDULE[now.day]
            for spawns in SCHEDULE.values():
                for spawn in spawns:
                    if now > spawn:
                        continue       
                    wait = (spawn - now).total_seconds()
                    print(wait)
                    await asyncio.sleep(wait)
                    self.bag_synced = True
                    return
                    
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
            f"Members can now type `{self.bot.command_prefix}bag add` & `{self.bot.command_prefix}bag remove` "
            "to enable bag alerts."
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

    @bag.command(name="next")
    async def bag_next(self, ctx: commands.Context) -> None:
        now = get_now_time()
        for day, spawns in SCHEDULE.items():
            if now.day > day:
                continue
            for spawn in spawns:
                if now > spawn:
                    continue
                spawn += timedelta(seconds=BRONJAM_ALERT_ADVANCE)
                diff = (spawn - now).total_seconds()
                return await ctx.send(f"Next spawn is in **{format_time(diff)}**. ({spawn})")

    @bag.command(name="schedule")
    async def bag_schedule(self, ctx: commands.Context) -> None:
        LIMIT = 5 # move this somewhere sensible
        out_spawns = []
        i = 0
        now = get_now_time()
        for spawns in SCHEDULE.values():
            if i >= LIMIT:
                break
            for spawn in spawns:
                if i >= LIMIT:
                    break # wtb labeled break from Golang
                if now > spawn:
                    continue
                out_spawns.append(spawn)
                i += 1

        if not out_spawns:
            return await ctx.send("No more spawns scheduled!")
        
        out = [f"`{spawn + timedelta(seconds=BRONJAM_ALERT_ADVANCE)}`" for spawn in out_spawns]

        await self.send_embed_message(
            ctx, 
            title=f"Next {len(out_spawns)} bag spawn times\n",
            description="\n".join(out)
        )
