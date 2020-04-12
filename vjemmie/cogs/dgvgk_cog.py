import socket
import time
from datetime import datetime, timedelta
import json
from typing import Dict

import discord
from discord.ext import commands
import trueskill

from .base_cog import BaseCog
from ..ladder import load_players, make_teams, rate, Player, Game, PLAYERS_FILE, ENV_FILE
from ..utils.exceptions import CommandError
from ..utils.serialize import dump_json
from ..utils.caching import get_cached
from ..utils.checks import dgvgk_cmd
from ..utils.voting import vote, SESSIONS


TIDSTYVERI_FILE = "db/dgvgk/tidstyveri.json"


class DGVGKCog(BaseCog):

    EMOJI = "<:julius:695298300257239081>"

    DIRS = ["db/dgvgk", "db/dgvgk/ladder"]
    FILES = [TIDSTYVERI_FILE, PLAYERS_FILE, ENV_FILE]

    def __init__(self, bot: commands.Bot) -> None:
        super().__init__(bot)
        self.tidstyver = {}
        self.game = None

    def save_tidstyveri(self, tidstyveri: dict) -> None:
        try:
            t = json.dumps(tidstyveri)
            with open(TIDSTYVERI_FILE, "w") as f:
                f.write(t)
        except:
            raise CommandError("Kan ikke lagre tidstyveri. Oops.")

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
    @vote(votes=2)
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
        tidstyver = sorted(
                [(self.bot.get_user(int(k)), v) for k, v in time_thiefs.items()],
                key=lambda i: i[1],
                reverse=True
        )
        
        tidstyver = {k: self.formater_tidstyveri(v) for k, v in tidstyver}
        
        embed = await self.format_key_value_embed(ctx, tidstyver, sort=False, title="Tidstyver")
        await ctx.send(embed=embed)
        
    @commands.group(name="inhouse", aliases=["ih"])
    async def inhouse(self, ctx: commands.Context) -> None:
        if not ctx.invoked_subcommand:
            await ctx.send(self.bot.get_command("help", "inhouse"))

    @inhouse.command(name="teams", aliases=["start", "create"])
    async def inhouse_teams(self, ctx: commands.Context, *ignored) -> None:
        ignored_users = [
            await commands.MemberConverter().convert(ctx, user) 
            for user in ignored
        ]
        
        # Make list of Discord user ID of participants
        userids = [
            user.id for user 
            in ctx.message.author.voice.channel.members
            if user not in ignored_users
        ]

        if len(userids) < 2:
            raise CommandError("At least 2 players are required to start a game!")

        # Load existing players from db
        players = {
            int(uid): player 
            for uid, player in load_players().items()
            if uid in userids
        }

        # Add new players (if they exist)
        for userid in userids:
            if userid not in players:
                players[userid] = Player(uid=userid, 
                                         rating=trueskill.Rating())

        game = make_teams(players, team_size=len(players)//2)
        
        await self.post_game_info(ctx, game)

        self.game = game

    async def post_game_info(self, ctx: commands.Context, game: Game) -> None:
        def get_team_str(team: Dict[int, Player], n: int) -> str:
            return (f"Team {n}\n```\n" + "\n".join(
                        f"* {self.bot.get_user(p.uid).name.ljust(20)} "
                        f"({round(p.rating.mu*40)})" for p in team) + "\n```"
                    )
        description = (
            f"{get_team_str(game.team1, 1)}\n"
            f"{get_team_str(game.team2, 2)}\n"
            f"Team 1 Win Probability: {round(game.win_probability*100)}%"
        )
        await self.send_embed_message(ctx, title="Teams", description=description)
    
    @inhouse.command(name="winner", aliases=["win", "w"])
    async def inhouse_winner(self, ctx: commands.Context, winner: str=None) -> None:
        if not self.game:
            raise CommandError("No game is currently in progress!")

        if not winner:
            raise CommandError(
                "Winner team argument must be one of `<n>`, `team <n>`, `team<n>`, `t<n>`\n"
                f"Example: `{self.bot.command_prefix}{ctx.invoked_with} team1`"
            )
        
        t1_win = winner in ["1", "team 1", "team1", "t1"]
        if t1_win:
            winners, losers = self.game.team1, self.game.team2
        else:
            winners, losers = self.game.team2, self.game.team1
        
        rate(winners, losers)
        
        self.game = None

        await ctx.send(
            f"Successfully registered a win for team {1 if t1_win else 2}. "
            "Rating has been updated."
        )

    @inhouse.command(name="game")
    async def inhouse_game(self, ctx: commands.Context) -> None:
        if not self.game:
            return await ctx.send("No game is currently in progress!")
        await self.post_game_info(ctx, self.game)

    @inhouse.command(name="stats", aliases=["leaderboard", "leaderboards"])
    async def inhouse_stats(self, ctx: commands.Context) -> None:
        players = load_players()
        if not players:
            raise CommandError("No players on record!")
        
        players = sorted(players.values(), key=lambda p: p.rating.mu, reverse=True)
        
        description = "\n".join([await self.fmt_player_stats(p, i) for i, p in enumerate(players, 1)])
        top_player_url = self.bot.get_user(players[0].uid).avatar_url
        
        await self.send_embed_message(ctx, 
                                      title="DGVGK Inhouse Rankings", 
                                      description=description, 
                                      thumbnail_url=top_player_url)

    async def fmt_player_stats(self, player: Player, n: int) -> str:
        return (f"**{n}. {self.bot.get_user(player.uid).name}**\n"
                f"Rating: {round(player.rating.mu*40)}\n"
                f"Matches: {player.wins+player.losses}\n"
                f"Wins: {player.wins}\n"
                f"Losses: {player.losses}\n")

    @inhouse.command(name="init")
    async def inhouse_init(self, ctx: commands.Context) -> None:
        pass