import socket
import time
from datetime import datetime, timedelta
import json

import discord
from discord.ext import commands
import mcstatus

from .base_cog import BaseCog
from ..utils.exceptions import CommandError
from ..utils.serialize import dump_json
from ..utils.caching import get_cached
from ..utils.checks import dgvgk_cmd


TIDSTYVERI_FILE = "db/dgvgk/tidstyveri.json"


class DGVGKCog(BaseCog):

    EMOJI = "<:julius:695298300257239081>"

    DIRS = ["db/dgvgk"]
    FILES = [TIDSTYVERI_FILE]

    def __init__(self, bot: commands.Bot) -> None:
        super().__init__(bot)
        self.tidstyver = {}

    def save_tidstyveri(self, tidstyveri: dict) -> None:
        try:
            t = json.dumps(tidstyveri)
        except:
            raise CommandError("Kan ikke lagre tidstyveri. Oops.")

        with open(TIDSTYVERI_FILE, "w") as f:
            f.write(t)

    def load_tidstyveri(self) -> dict:
        with open(TIDSTYVERI_FILE, "r") as f:
            try:
                return json.load(f)
            except:
                return {}
    
    def formater_tidstyveri(self, tid: float) -> None:
        td = timedelta(seconds=tid)
        s = ""
        
        hours = td.seconds // 3600
        if hours:
            s += f"{str(hours).rjust(2, '0')}t " # only show hours if necessary

        minutes = (td.seconds // 60) % 60
        if minutes or hours: # show minutes if hours are shown
            s += f"{str(minutes).rjust(2, '0')}m " 

        s += f"{str(td.seconds - (hours * 3600) - (minutes * 60)).rjust(2, '0')}s"
        return s
        
    @commands.group(name="tidstyveri", aliases=["tidstyv", "tt"], usage="<subcommand>")
    async def tidstyveri(self, ctx: commands.Context) -> None:
        """Tidstyveri-kommandoer"""
        if not ctx.invoked_subcommand:
            await ctx.invoke(self.bot.get_command("help"), "tidstyveri")

    @tidstyveri.command(name="start")
    async def tidstyveri_start(self, ctx: commands.Context, member: commands.MemberConverter=None) -> None:
        """Registrer påbegynt tyveri"""
        if not member:
            raise CommandError("Et discord-brukernavn er påkrevd!")
        
        self.tidstyver[str(member.id)] = time.time()

        await ctx.send(f"Registrerer at et tidstyveri begått av {member.name} er underveis.")
        
    @tidstyveri.command(name="stop", aliases=["stopp"])
    async def tidstyveri_stop(self, ctx: commands.Context, member: commands.MemberConverter=None) -> None:
        """Stopp tyveri"""
        if not member:
            raise CommandError("Et discord-brukernavn er påkrevd!")
        
        start_time = self.tidstyver.pop(str(member.id), None)
        if not start_time:
            raise CommandError("Det er ikke registrert et påbegynt tidstyveri for denne personen!")
        
        time_thiefs = self.load_tidstyveri()
        
        time_stolen = time.time() - start_time
        time_thiefs[str(member.id)] = time_thiefs.get(str(member.id), 0) + time_stolen
        
        self.save_tidstyveri(time_thiefs)

        await ctx.send(
            f"Registrert fullført tidstyveri.\n"
            f"{member.name} stjal {self.formater_tidstyveri(time_stolen)}\n"
            f"{member.name} har totalt stjålet {self.formater_tidstyveri(time_thiefs[str(member.id)])}!"
        )
        
    @tidstyveri.command(name="stats")
    async def tidstyveri_stats(self, ctx: commands.Context) -> None:
        """Tyv-leaderboard"""
        time_thiefs = self.load_tidstyveri()
        if not time_thiefs:
            raise CommandError("Ingen tidstyver er registrert!")
        
        # Sort users by amount of time stolen
        tidstyver = dict(
            sorted(
                [(self.bot.get_user(int(k)), v) for k, v in time_thiefs.items()],
                key=lambda i: i[1],
                reverse=True
            )
        )
        tidstyver = {k: self.formater_tidstyveri(v) for k, v in tidstyver.items()}
        
        embed = await self.format_key_value_embed(ctx, tidstyver, sort=False, title="Tidstyver")
        await ctx.send(embed=embed)
        
