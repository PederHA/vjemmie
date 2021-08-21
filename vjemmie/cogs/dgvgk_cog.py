import json
import time
from typing import Dict, List, Optional

import trueskill
from aiofile import AIOFile
from discord.ext import commands

from ..db import db
from ..ladder import (
    ENV_FILE,
    PLAYERS_FILE,
    Match,
    Player,
    dump_players,
    get_new_player,
    load_players,
    make_teams,
    rate,
)
from ..utils.checks import admins_only, dgvgk_cmd
from ..utils.converters import NonCaseSensMemberConverter
from ..utils.exceptions import CommandError
from ..utils.json import dump_json
from ..utils.voting import SESSIONS, TopicType, vote
from .base_cog import BaseCog

TIDSTYVERI_FILE = "db/dgvgk/tidstyveri.json"


class DGVGKCog(BaseCog):

    EMOJI = "<:julius:695298300257239081>"

    DIRS = ["db/dgvgk", "db/dgvgk/ladder"]
    FILES = [PLAYERS_FILE, ENV_FILE]

    def __init__(self, bot: commands.Bot) -> None:
        super().__init__(bot)
        self.tidstyver: Dict[str, float] = {}
        self.game: Optional[Match] = None

    def formater_tidstyveri(self, seconds: float) -> str:
        s = ""
        seconds = round(seconds)

        hours = seconds // 3600
        if hours:
            # only show hours if necessary
            s += f"{str(hours).rjust(2, '0')}t "

        minutes = (seconds // 60) % 60
        if minutes or hours:  # show minutes if hours are shown
            s += f"{str(minutes).rjust(2, '0')}m "

        s += f"{str(seconds - (hours * 3600) - (minutes * 60)).rjust(2, '0')}s"
        return s

    @commands.group(name="tidstyveri", aliases=["tidstyv", "tt"], usage="<subcommand>")
    async def tidstyveri(self, ctx: commands.Context) -> None:
        """Tidstyveri-kommandoer"""
        if not ctx.invoked_subcommand:
            await ctx.invoke(self.bot.get_command("help"), "tidstyveri")

    @tidstyveri.command(name="start")
    @vote(votes=2, topic=TopicType.member)
    async def tidstyveri_start(
        self, ctx: commands.Context, member: NonCaseSensMemberConverter = None
    ) -> None:
        """Registrer påbegynt tyveri"""
        if not member:
            raise CommandError("Et discord-brukernavn er påkrevd!")
        elif str(member.id) in self.tidstyver:
            raise CommandError("Denne brukeren stjeler allerede tid!")
        # elif member.id == self.bot.user.id:
        #    raise CommandError("Kan ikke starte tidstyveri for botten selv!")

        self.tidstyver[str(member.id)] = time.time()

        # TODO: User mention
        await ctx.send(
            f"Registrerer at et tidstyveri begått av {member.name} er underveis."
        )

    @tidstyveri.command(name="stop", aliases=["stopp"])
    async def tidstyveri_stop(
        self, ctx: commands.Context, member: NonCaseSensMemberConverter = None
    ) -> None:
        """Stopp tyveri"""
        if not member:
            raise CommandError("Et discord-brukernavn er påkrevd!")

        start_time = self.tidstyver.pop(str(member.id), None)
        if not start_time:
            raise CommandError(
                "Det er ikke registrert et påbegynt tidstyveri for denne personen!"
            )

        # Store time stolen
        time_stolen = time.time() - start_time
        await db.add_tidstyveri(member, time_stolen)

        # Get total time stolen
        stolen = await db.get_tidstyveri_by_id(member.id)

        await ctx.send(
            f"Registrert fullført tidstyveri.\n"
            f"{member.name} stjal {self.formater_tidstyveri(time_stolen)}\n"
            f"{member.name} har totalt stjålet {self.formater_tidstyveri(stolen)}!"
        )

    @tidstyveri.command(name="stats")
    async def tidstyveri_stats(self, ctx: commands.Context) -> None:
        """Tyv-leaderboard"""
        time_thiefs = await db.get_tidstyveri()
        if not time_thiefs:
            raise CommandError("Ingen tidstyver er registrert!")

        tidstyver = {k: self.formater_tidstyveri(v) for k, v in time_thiefs}

        await self.send_key_value_message(
            ctx, tidstyver, title="Tidstyveri", sort=False
        )

    @commands.group(name="inhouse", aliases=["ih"], enabled=False)
    @dgvgk_cmd()
    async def inhouse(self, ctx: commands.Context) -> None:
        if not ctx.invoked_subcommand:
            await ctx.invoke(self.bot.get_command("help"), "inhouse")

    @inhouse.command(name="teams", aliases=["start", "create"])
    async def inhouse_teams(self, ctx: commands.Context, *ignored) -> None:
        ignored_users = [
            await NonCaseSensMemberConverter().convert(ctx, user) for user in ignored
        ]

        # Make list of Discord user ID of participants
        userids = [
            user.id
            for user in await self.get_members_in_voice_channel(ctx)
            if user not in ignored_users
        ]

        if len(userids) < 2:
            raise CommandError("At least 2 players are required to start a game!")
        elif len(userids) % 2 != 0:
            raise CommandError("Can only create teams for an even number of players!")

        # Load existing players from db
        players = {
            int(uid): player for uid, player in load_players().items() if uid in userids
        }

        # Add new players (if there are any)
        for userid in userids:
            if userid not in players:
                players[userid] = get_new_player(int(userid))

        game = make_teams(players, team_size=len(players) // 2)

        await self.post_game_info(ctx, game)

        self.game = game

    async def post_game_info(self, ctx: commands.Context, game: Match) -> None:
        def get_team_str(team: List[Player], n: int) -> str:
            return (
                f"Team {n}\n```\n"
                + "\n".join(
                    f"* {self.bot.get_user(p.uid).name.ljust(20)}" for p in team
                )
                + "\n```"
            )

        description = (
            f"{get_team_str(game.team1, 1)}\n"
            f"{get_team_str(game.team2, 2)}\n"
            f"Team 1 Win Probability: {round(game.win_probability*100)}%"
        )
        await self.send_embed_message(ctx, title="Teams", description=description)

    @inhouse.command(name="winner", aliases=["win", "w"])
    async def inhouse_winner(self, ctx: commands.Context, winner: str = None) -> None:
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

        try:
            rate(winners, losers)
        except:
            await self.log_error(ctx)  # Not ideal, is it?
            raise CommandError("Something went wrong when attempting to update rating!")

        self.game = None

        await ctx.send(f"Successfully registered a win for team {1 if t1_win else 2}. ")

    @inhouse.command(name="game")
    async def inhouse_game(self, ctx: commands.Context) -> None:
        if not self.game:
            return await ctx.send("No game is currently in progress!")
        await self.post_game_info(ctx, self.game)

    @inhouse.command(name="stats", aliases=["leaderboard", "leaderboards"])
    @admins_only()
    async def inhouse_stats(self, ctx: commands.Context) -> None:
        players = load_players()
        if not players:
            raise CommandError("No players on record!")

        plist = sorted(players.values(), key=lambda p: p.rating.mu, reverse=True)

        description = "\n".join(
            [await self.fmt_player_stats(p, i) for i, p in enumerate(plist, 1)]
        )
        top_player_url = self.bot.get_user(plist[0].uid).avatar_url

        await self.send_embed_message(
            ctx,
            title="DGVGK Inhouse Rankings",
            description=description,
            thumbnail_url=top_player_url,
        )

    async def fmt_player_stats(self, player: Player, n: int) -> str:
        return (
            f"**{n}. {self.bot.get_user(player.uid).name}**\n"
            f"Rating: {round(player.rating.mu*40)}\n"
            f"Matches: {player.wins+player.losses}\n"
            f"Wins: {player.wins}\n"
            f"Losses: {player.losses}\n"
        )

    @inhouse.command(name="init")
    async def inhouse_init(self, ctx: commands.Context) -> None:
        pass

    @inhouse.command(name="cancel")
    async def inhouse_cancel(self, ctx: commands.Context) -> None:
        if not self.game:
            raise CommandError("No game is currently in progress!")

        self.game = None

        await ctx.send("Successfully cancelled the game.")

    @inhouse.command(name="reset")
    @admins_only()
    async def inhouse_reset(self, ctx: commands.Context) -> None:
        players = load_players()
        if not players:
            await ctx.send("Nothing to be done. No players in db.")
            return

        for uid in players:  # We don't even need to iterate over values
            players[uid] = get_new_player(uid)
        dump_players(players)

        await ctx.send("Successfully reset stats for all players!")

    @inhouse.command(name="adjust")
    @admins_only()
    async def inhouse_adjust(
        self,
        ctx: commands.Context,
        player: NonCaseSensMemberConverter,
        new_rating: float,
    ) -> None:
        """Adjusts the rating of a specific player.
        NOTE: This WILL create rating inflation/deflation.
        """
        if new_rating >= 1000:
            new_rating = new_rating / 40

        players = load_players()

        orig_rating = players[player.id].rating
        players[player.id].rating = trueskill.Rating(
            mu=new_rating, sigma=orig_rating.sigma
        )

        dump_players(players)

        await ctx.send(
            f"Changed **{player.name}**'s rating from {orig_rating.mu*40} to {new_rating*40}!"
        )
