import asyncio
import math
import sqlite3
import traceback
from itertools import combinations, chain
from typing import Tuple
from collections import namedtuple
from pprint import pprint

import discord
import trueskill
from discord.ext import commands

from cogs.base_cog import BaseCog
from cogs.db_cog import DatabaseHandler
from ext.checks utils import is_dgvgk


class War3Cog(BaseCog):
    def __init__(self, bot: commands.Bot, log_channel_id: int, replays_folder: str=None) -> None:
        super().__init__(bot, log_channel_id)
        self.replays_folder = replays_folder
        self.db = DatabaseHandler("db/rating.db")
        self.base_rating = 25
        trueskill.setup(sigma=2.5)

    
    @commands.command(name="add")
    @is_dgvgk()
    async def add_user(self, ctx: commands.Context, user_id: int, realname: str=None, game="legiontd") -> None:
        for member in self.bot.get_all_members():
            # This is the only way I found to obtain an arbitrary user's nickname
            # self.bot.get_user() returns a User obj, which does not have a nick attribute
            if member.id == user_id:
                user = member
        if user is not None:
            msg = self.db.add_user(user, realname, game, self.base_rating)
            await ctx.send(msg)
    
    @commands.command(name="leaderboard")
    @is_dgvgk()
    async def leaderboard(self, ctx: commands.Context, game="legiontd", alias: bool=False, *, post_game: bool=False) -> None:
        players = self.db.get_players(game, alias=alias)
        output = "```\nDGVGK Legion TD Rankings:\n\n"
        for player in players:
            name, rating, wins, losses = player
            if not (wins == 0 and losses == 0):
                name = name.capitalize()
                rating = round(rating*40)
                if len(name) > 10:
                    name = name[:10]
                # Align rows. Kinda hacky, looking for better solution.
                name_spc = " " * (10 - len(name))
                rating_spc = " " * (10 - len(str(rating)))
                wins_spc = " " * (6 - len(str(wins)))
                output += f"{name}{name_spc}\tRating: {rating}{rating_spc}Wins: {wins}{wins_spc}Losses: {losses}\n"
        output += "```"
        if post_game:
            deletion_timer = 60.0
        else:
            deletion_timer = None
        await ctx.send(output, delete_after=deletion_timer)
        
    
    @commands.command(name="result")
    @is_dgvgk()
    async def result(self, ctx:commands.Context, winners: str, losers: str=None, game="legiontd", alias: bool=False, preview: bool=False):
        """
        Report result of a game, resulting in a rating update for the players involved.

        Discord message example:
            !result "player1 player2" "player3 player4"
        
        Winners and losers are passed in as separate strings. Players are separated 
        by spaces.
        """

        def pred(m: discord.Message) -> bool:
                    return m.author == ctx.message.author and m.channel == ctx.message.channel
        
        # List from string of names separated by spaces. Remove duplicates.
        winners = list(set(winners.lower().split(" "))) 
        # Copy of winners that will not be modified
        winners_names = list(winners)    
        if losers is not None:
            losers = list(set(losers.lower().split(" ")))
            losers_names = list(losers)
        else:
            # Detect losing team from voice channel if `losers` is None
            _voice_chatters = await self.get_users_in_voice(ctx)
            losers = list(set(_voice_chatters) - set(winners))
            if len(losers) > len(winners):
                losers_str = ", ".join(losers)
                await ctx.send(f"Detected uneven teams. Is this the correct losing team?\n{losers_str}\n"
                               "Type **yes** to confirm and **no** to abort rating update.")
                try:
                    msg = await self.bot.wait_for("message", check=pred, timeout=10.0)
                except asyncio.TimeoutError:
                    await ctx.send("No reply from user. Aborting.")
                    raise Exception("User did not reply to confirmation prompt.")
                if msg.content.lower() not in  ["yes", "y", "ja"]:
                    await ctx.send("Aborting rating update.")
                    raise Exception
        
        # Could use sets for this as well, but this is pretty clear
        for name in winners:
            if name in losers:
                await ctx.send(f"{name} cannot be on both teams.")
                raise Exception("!add: Duplicate name on winning and losing team")
        
        # Get players from db as list of namedtuples        
        players = self.db.get_players(game, alias=alias)
        _players = [player.name for player in players]
        
        # Lists holding Player tuples that will replace winners/losers after names are parsed
        _winners = []
        _losers = []        

        # Loops until all players are parsed
        while len(_winners+_losers) != len(winners+losers):
            for winner in winners:
                for player in players:
                    if player.name == winner:
                        _winners.append(player)
                        break    
            for loser in losers:
                for player in players:    
                    if player.name == loser:
                        _losers.append(player)
                        break                 
            # Prompt to add player to database if player is not found in db
            unknown_players = [name for name in winners+losers if name not in _players]
            if unknown_players:
                for name in unknown_players:
                    abort = "abort"
                    cmd = self.bot.get_command("add")
                    await ctx.send(f"Could not find player {name}.\n" 
                                f"Add {name} to database by typing: `<User ID> (optional: <Real Name>)`.\n"
                                f"Type **{abort}** to abort")               
                    try:
                        msg = await self.bot.wait_for("message", check=pred, timeout=15.0)
                    # Raise exception if 15 seconds pass without reply from user
                    except asyncio.TimeoutError:
                        await ctx.send("No reply from user. Aborting.")
                        raise Exception
                    
                    # If user responds, check message content
                    if msg.content.lower() == abort:
                        await ctx.send("Aborting. Rating will not be updated.")
                        raise Exception("Rating update aborted by user.")    
                    else:
                        user_id, *realname = msg.content.split(" ")
                        if realname != []:
                            realname = realname[0]
                        else:
                            realname = None
                        try:
                            user_id = int(user_id)
                        except:
                            await ctx.send("User ID must be an integer. Aborting.")
                            raise Exception(f"User provided non-int user_id: {user_id}")
                        else:
                            await ctx.invoke(cmd, user_id, realname, game)
                            players = self.db.get_players(game, alias=False)
                            _players = [player for player, _, _, _ in players]

        else:
            # After loop, replace lists of names with list of player tuples (name, rating, wins losses)
            winners = _winners
            losers = _losers

        # Create trueskill.Rating objects for players
        ts_winners = []
        for winner in winners:
            _winner = trueskill.Rating(mu=winner.rating)
            ts_winners.append(_winner)
        ts_losers = []
        for loser in losers:
            _loser = trueskill.Rating(mu=loser.rating)
            ts_losers.append(_loser)            

        # Calculate new ratings
        if (len(winners) + len(losers)) % 2 == 0:
            winners_new, losers_new = trueskill.rate([tuple(ts_winners), tuple(ts_losers)])
        else:
            # Tune rating changes in uneven matches
            # Placeholder value. I have no idea how to tune this right now.
            quality = 1
            if len(ts_winners) > len(ts_losers):
                winners_new, losers_new = trueskill.rate([tuple(ts_winners), tuple(ts_losers)], 
                                          weights=[tuple([quality for i in winners]), tuple([quality for x in losers])])
            else:
                winners_new, losers_new = trueskill.rate([tuple(ts_winners), tuple(ts_losers)], 
                            weights=[tuple([quality for i in winners]), tuple([quality for x in losers])])
        
        if not preview:
            def update_rating(names: list, players_pre: list, players_post: list, db, *, win: bool, game: str) -> str:
                """
                Updates winners/losers ratings and generates string displaying
                rating change, used in discord message.
                """
                _msg = ""
                for idx, player in enumerate(players_post):
                    # Update player rating in DB
                    db.update_rating(names[idx], player, win=True, game=game)
                    # Rounded numbers for output msg
                    pre_rating = round(players_pre[idx].mu*40)
                    post_rating = round(player.mu*40)
                    rating_change = round(post_rating - pre_rating)
                    if rating_change > 0:
                        symbol = "+"
                    else:
                        symbol = ""
                    _msg += f"{names[idx].capitalize()}: {pre_rating} -> {post_rating} ({symbol}{rating_change})\n"
                return _msg
            
            # Update ratings in DB and generate Discord message 
            msg = "```Rating change:\n\n"
            msg += update_rating(winners_names, ts_winners, winners_new, self.db, win=True, game=game)
            msg += update_rating(losers_names, ts_losers, losers_new, self.db, win=False, game=game) 
            msg += "```"

            # Post rating change message
            await ctx.send(msg, delete_after=60.0)
            cmd = self.bot.get_command("leaderboard")
            # Post overall leaderboard
            await ctx.invoke(cmd, game, post_game=True)
        
        elif preview:
            # Rating change is the same for all players in a team
            rating_gain = round((winners_new[0].mu - ts_winners[0].mu)*40) # Index is irrelevant
            rating_loss = round((ts_losers[0].mu - losers_new[0].mu)*40)
            return rating_gain, rating_loss

    @commands.command(name="teams")
    @is_dgvgk()
    async def autobalance(self, ctx: commands.Context, players: str=None, game: str="legiontd") -> None:
        """
        Distributes players to 2 teams based on their rating.
        """

        MIN_PLAYERS = 3

        help_str = """Usage: !teams "player1 player2 player3 player4" (opt: <game>)
                      If command is called without arguments, pulls players from 
                      message author's voice channel."""
        
        if players is None or players == "c":
            # Get players from author's voice channel if no argument to param `players` is given
            players = await self.get_users_in_voice(ctx)
            if players is None or players is []:
                await ctx.send("You are not connected to a voice channel")
                raise discord.DiscordException("User is not connected to a voice channel")
            elif len(players) < MIN_PLAYERS:
                await ctx.send(f"At least {MIN_PLAYERS} players have to be present in the voice channel.")
                raise Exception
        else:
            # Create list from string of names separated by spaces
            players = players.split(" ")

        if len(players) < MIN_PLAYERS:
            await ctx.send("A minimum of 3 players is required.")
            raise ValueError("Need at least 3 players to make teams")
        
        try:
            db_players = self.db.get_players(game)
        except sqlite3.OperationalError:
            err = traceback.format_exc()
            await self.send_log(err)
            await ctx.send(f"Could not find player stats for game **{game}**.")
            raise
        
        players_ratings = []
        for db_player in db_players:
            for player in players:
                if db_player.name == player:
                    players_ratings.append(db_player)
                    break

        n_players = len(players_ratings)
        # Generate all possible team combinations of size len(players)/2 rounded up
        _combs = combinations(players_ratings, r=(math.ceil((n_players)/2)))
        # Sort list of player combinations by sum of player ratings from low->high
        combs = sorted(_combs, key=lambda x: sum([rating for _, rating, _, _ in x]))
        if n_players % 2 == 0:
            # Find team on middle index, which should have the most balanced complement
            middle = (len(combs) / 2) - .5
            if middle % 2 != 0:
                # +.5 or -.5 is irrelevant, the matchup will always be the same
                # -.5 is the complement of +.5
                team1 = combs[int(middle+.5)]
            else:              
                team1 = combs[int(middle)]
        elif n_players == 1:
            # This shouldn't happen, but somehow it did happen once. Investigating.
            raise Exception
        else:
            # If teams are uneven, stack the biggest team with the worst players
            # Lazy implementation for now
            team1 = combs[0]
        
        # Team2 is determined from difference players-team1
        team2 = list(set(players_ratings) - set(team1))

        async def calc_team_rating(team: list) -> Tuple[float, str]:
            team_rating = 0
            _team_names = []
            for player in team:
                _team_names.append(f"{player.name.capitalize()} ({round(player.rating*40)})")
                team_rating += player.rating*40
            team_rating = round(team_rating/len(team))
            team_names = ", ".join(_team_names)
            team_spaces = " "*(40-len(team_names))
            t = " ".join([name for name, _, _, _ in team])
            return team_rating, team_names, team_spaces, t
        
        # Get formatted ratings, names(rating), spaces, names for output message
        team1_rating, team1_names, t1_spaces, t1 = await calc_team_rating(team1)
        team2_rating, team2_names, t2_spaces, t2 = await calc_team_rating(team2)

        # Get potential rating change for win AND loss for both teams
        rating_change_cmd = self.bot.get_command("result")
        team1_win, team2_loss = await ctx.invoke(rating_change_cmd, winners=t1, losers=t2, preview=True)
        team2_win, team1_loss = await ctx.invoke(rating_change_cmd, winners=t2, losers=t1, preview=True)

        # Create message  
        msg = "```"
        msg += f"Team 1: {team1_names}{t1_spaces}\t+{team1_win}/-{team1_loss}\tAverage rating: {team1_rating}\n"
        msg += f"Team 2: {team2_names}{t2_spaces}\t+{team2_win}/-{team2_loss}\tAverage rating: {team2_rating}\n"
        msg += "```"
        await ctx.send(msg)