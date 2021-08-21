import json
import math
import random
from dataclasses import dataclass, field, is_dataclass
from itertools import chain, combinations
from typing import Dict, List, Tuple

import trueskill
from loguru import logger
from trueskill import BETA, MU, SIGMA, Rating

PLAYERS_FILE = "db/dgvgk/ladder/players.json"
ENV_FILE = "db/dgvgk/ladder/env.json"

DEFAULT_MU = MU
DEFAULT_SIGMA = SIGMA


def load_env() -> None:
    env = None
    try:
        with open(ENV_FILE, "r") as f:
            env = json.load(f)
    except FileNotFoundError:
        pass
    except json.JSONDecodeError:
        logger.warning(f"Failed to read '{ENV_FILE}'")
    finally:
        if env:
            trueskill.setup(mu=env["mu"], sigma=env["sigma"])
        else:
            trueskill.setup(mu=DEFAULT_MU, sigma=DEFAULT_SIGMA)


load_env()


@dataclass
class Player:
    uid: int
    rating: Rating
    wins: int = 0
    losses: int = 0
    draws: int = 0

    def asdict(self) -> dict:
        d = {
            "uid": self.uid,
            "rating": {
                "mu": self.rating.mu,
                "sigma": self.rating.sigma,
            },
            "wins": self.wins,
            "losses": self.losses,
            "draws": self.draws,
        }
        return d


@dataclass
class Match:
    """Represents a potential match by the matchmaker."""

    team1: List[Player] = field(default_factory=list)
    team2: List[Player] = field(default_factory=list)
    win_probability: float = 0.0


def dump_players(players: Dict[int, Player]) -> None:
    class EnhancedJSONEncoder(json.JSONEncoder):
        def default(self, o):
            if is_dataclass(o):
                return o.asdict()
            return super().default(o)

    with open("db/dgvgk/ladder/players.json", "w") as f:
        json.dump(players, f, cls=EnhancedJSONEncoder, indent=4)


def load_players() -> Dict[int, Player]:
    with open(PLAYERS_FILE, "r") as f:
        players = json.load(f)

    return {
        int(uid): Player(
            uid=int(uid),
            rating=Rating(mu=player["rating"]["mu"], sigma=player["rating"]["sigma"]),
            wins=player.get("wins", 0),
            losses=player.get("losses", 0),
            draws=player.get("draws", 0),
        )
        for uid, player in players.items()
    }


def make_teams(players: Dict[int, Player], team_size: int = 4) -> Match:
    """
    Tries to find the most balanced team combination.
    I am literally the worst at math.
    """
    p = sorted([p for p in players.values()], key=lambda p: p.rating)
    comb = list(combinations(p, team_size))

    matches = []
    # Brute-force, because we are stupid like that
    for pt1 in comb:
        for pt2 in comb:
            if len(list(set(p.uid for p in pt1 + pt2))) == len(comb[0]) * 2:
                prob = win_probability(pt1, pt2)
                matches.append(Match(team1=pt1, team2=pt2, win_probability=prob))
    best = min(matches, key=lambda g: abs(g.win_probability - 0.5))
    return best


def rate(
    winners: List[Player], losers: List[Player]
) -> Tuple[List[Player], List[Player]]:
    w = {p.uid: p.rating for p in winners}
    l = {p.uid: p.rating for p in losers}

    w, l = trueskill.rate([w, l], ranks=[0, 1])

    update_rating(w, l)

    return winners, losers


def update_rating(winners: Dict[int, Player], losers: Dict[int, Player]) -> None:
    players = load_players()

    def update(team: Dict[int, Player], win: bool = True):
        for uid, rating in team.items():
            if uid not in players:
                players[uid] = Player(uid=uid, rating=rating)
            else:
                players[uid].rating = rating

            if win:
                players[uid].wins += 1
            else:
                players[uid].losses += 1

    update(winners)
    update(losers, win=False)
    dump_players(players)


def win_probability(team1, team2):
    """Ripped from trueskill.org"""
    team1r = [p.rating for p in team1]
    team2r = [p.rating for p in team2]
    delta_mu = sum(r.mu for r in team1r) - sum(r.mu for r in team2r)
    sum_sigma = sum(r.sigma ** 2 for r in chain(team1r, team2r))
    size = len(team1r) + len(team2r)
    denom = math.sqrt(size * (BETA * BETA) + sum_sigma)
    ts = trueskill.global_env()
    return ts.cdf(delta_mu / denom)


def get_new_player(uid: int) -> Player:
    return Player(uid=int(uid), rating=Rating())
