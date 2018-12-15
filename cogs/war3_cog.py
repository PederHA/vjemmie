import asyncio
import math
import sqlite3
import traceback
from itertools import combinations
from typing import Tuple

import discord
import trueskill
from discord.ext import commands

from cogs.base_cog import BaseCog
from cogs.db_cog import DatabaseHandler


class War3Cog(BaseCog):
    def __init__(self, bot: commands.Bot, log_channel_id: int, replays_folder: str) -> None:
        super().__init__(bot, log_channel_id)
        self.replays_folder = replays_folder
        self.db = DatabaseHandler("db/rating.db")
        self.base_rating = 25
        trueskill.setup(sigma=2.5)

    
    @commands.command(name="add")
    async def add_user(self, ctx: commands.Context, user_id: int, realname: str, game="legiontd") -> None:
        for member in self.bot.get_all_members():
            # This is the only way I found to obtain an arbitrary user's nickname
            # self.bot.get_user() returns a User obj, which does not have a nick attribute
            if member.id == user_id:
                user = member
        if user is not None:
            msg = self.db.add_user(user, realname, game, self.base_rating)
            await ctx.send(msg)
    
    @commands.command(name="leaderboard")
    async def leaderboard(self, ctx: commands.Context, game="legiontd", alias: bool=False, post_game: bool=False) -> None:
        players = self.db.get_players(game, alias=alias)
        output = "```\nDGVGK Legion TD Rankings:\n\n"
        for player in players:
            name, rating, wins, losses = player
            name = name.capitalize()
            rating = round(rating*40)
            if len(name) > 10:
                name = name[:10]
            # Align rows. Kinda hacky, looking for better solution.
            name_spc = " " * (10 - len(name))
            rating_spc = " " * (10 - len(str(rating)))
            wins_spc = " " * (6 - len(str(wins)))
            output += f"{name}{name_spc}\tRating: {rating}{rating_spc}Wins: {wins}{wins_spc}Losses: {losses}\n"
        else:
            output += "```"
            if post_game:
                deletion_timer = 60.0
            else:
                deletion_timer = None
            await ctx.send(output, delete_after=deletion_timer)
        
    
    @commands.command(name="result")
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
        winners.sort()  
        # Copy of winners that will not be modified
        winners_names = list(winners)    
        if losers is not None:
            losers = list(set(losers.lower().split(" ")))
            losers.sort()
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
        
        # Get players from db as list of tuples        
        players = self.db.get_players(game, alias=alias)
        _players = [player for player, _, _, _ in players]
        # Temporary lists that will replace winners/losers after names are parsed
        _winners = []
        _losers = []        

        def filter_participants(participant: str) -> None:
            """
            OMEGAGIGA ugly function for matching players in db with
            players in `winners` and `losers`.

            I don't like scattering specialized methods around in my Cogs. 
            Since this function will only ever be used by `result()`, 
            it is defined here.
            """

            nonlocal winners
            nonlocal _winners
            nonlocal losers
            nonlocal _losers
            nonlocal players
            nonlocal _players
            if participant in _players and not (participant in winners and participant in losers):
                for player, rating, wins, losses in players:
                    for winner in winners:
                        if player == winner:
                            _winners.append((player, rating, wins, losses))
                            winners.remove(player)
                            break
                    for loser in losers:    
                        if loser == player:
                            _losers.append((player, rating, wins, losses))
                            losers.remove(player)
                            break

        for participant in winners+losers:
            if participant in _players and not (participant in winners and participant in losers):
                filter_participants(participant)
            elif participant not in _players or (participant in winners and participant in losers):
                abort = "abort"
                cmd = self.bot.get_command("add")
                await ctx.send(f"Could not find player {participant}.\n" 
                               f"Add {participant} to database by typing user's User ID.\n"
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
                    user_id, *alias = msg.content.split(" ")
                    if alias != []:
                        alias = alias[0]
                    else:
                        alias = None
                    try:
                        user_id = int(user_id)
                    except:
                        await ctx.send("User ID must be an integer. Aborting.")
                        raise Exception(f"User provided non-int user_id: {user_id}")
                    else:
                        await ctx.invoke(cmd, user_id, alias, game)
                        players = self.db.get_players(game, alias=alias)
                        _players = [player for player, _, _, _ in players]
                        filter_participants(participant)

        winners = _winners
        losers = _losers
        ts_winners = []
        ts_losers = []
        
        # Create trueskill.Rating objects for players
        for winner in winners:
            name, rating, wins, losses = winner
            _winner = trueskill.Rating(mu=rating)
            ts_winners.append(_winner)
        for loser in losers:
            name, rating, wins, losses = loser
            _loser = trueskill.Rating(mu=rating)
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
        
        # Update ratings in DB and generate Discord message 
        if not preview: 
            msg = "```Rating change:\n\n"
            for idx, winner in enumerate(winners_new):
                self.db.update_rating(winners_names[idx], winner, win=True, game=game)
                rating_gain = round((winner.mu - ts_winners[idx].mu)*40)
                msg += f"{winners[idx][0].capitalize()}: +{rating_gain} rating.\n"
            for idx, loser in enumerate(losers_new):
                self.db.update_rating(losers_names[idx], loser, win=False, game=game)
                rating_loss = round((ts_losers[idx].mu - loser.mu)*40)
                msg += f"{losers[idx][0].capitalize()}: -{rating_loss} rating.\n"   
            msg += "```"

            # Post rating change message
            await ctx.send(msg, delete_after=60.0)
            cmd = self.bot.get_command("leaderboard")
            # Post overall leaderboard
            await ctx.invoke(cmd, game)
        
        if preview:
            # Rating change is the same for all players in a team
            rating_gain = round((winners_new[0].mu - ts_winners[0].mu)*40) # Index is irrelevant
            rating_loss = round((ts_losers[0].mu - losers_new[0].mu)*40)
            return rating_gain, rating_loss

    @commands.command(name="teams")
    async def autobalance(self, ctx: commands.Context, players: str=None, game: str="legiontd") -> None:
        """
        Distributes players to 2 teams based on their rating.
        """

        help_str = """Usage: !teams "player1 player2 player3 player4" (opt: <game>)
                      If command is called without arguments, pulls players from 
                      message author's voice channel."""
        
        if players is None or players == "c":
            # Get players from author's voice channel if no argument to param `players` is given
            players = await self.get_users_in_voice(ctx)
            if players is None:
                await ctx.send("You are not connected to a voice channel")
                raise Exception
            elif len(players) == 1:
                await ctx.send("At least 2 players have to be present in the voice channel.")
                raise Exception
        else:
            # Create list from string of names separated by spaces
            players = players.split(" ")
        
        try:
            db_players = self.db.get_players(game)
        except sqlite3.OperationalError:
            err = traceback.format_exc()
            await self.send_log(err)
            await ctx.send(f"Could not find player stats for game **{game}**.")
            raise Exception
        
        players_ratings = []
        for db_player in db_players:
            name, rating, wins, losses = db_player
            for player in players:
                if name == player:
                    players_ratings.append(db_player)
                    break
        
        n_players = len(players_ratings)
        _combs = combinations(players_ratings, r=(math.ceil((n_players)/2)))
        # Sort list of player combinations by sum of player ratings from low->high
        combs = sorted(_combs, key=lambda x: sum([rating for _, rating, _, _ in x]))
        # Generate team1
        if len(players_ratings) % 2 == 0:
            middle = float(len(combs))/2
            if middle % 2 != 0:
                # If middle index is not an integer, test both [middle + .5] and [middle - .5]

                # Calculate average rating for first potential team 1
                _t1_1 = combs[int(middle + .5)] 
                _t1_1_rating = sum([rating for _, rating, _, _ in _t1_1])
                _t2_1 = list(set(players_ratings) - set(_t1_1))
                _t2_1_rating = sum([rating for _, rating, _, _ in _t2_1])

                # Calculate average rating for second potential team 1
                _t1_2 = combs[int(middle - .5)]
                _t1_2_rating = sum([rating for _, rating, _, _ in _t1_2])
                _t2_2 = list(set(players_ratings) - set(_t1_2))
                _t2_2_rating = sum([rating for _, rating, _, _ in _t2_1])
                
                # Find difference in average rating for potential first team1 vs potential team2
                # Difference is a number >=0
                if _t1_1_rating >= _t2_1_rating:
                    diff1 = _t1_1_rating - _t2_1_rating
                else:
                    diff1 = _t2_1_rating - _t1_1_rating    
                # Same for second potential team1 vs second potential team2
                if _t1_2_rating >= _t2_2_rating:
                    diff2 = _t1_2_rating - _t2_2_rating
                else:
                    diff2 = _t2_2_rating - _t1_2_rating 
                
                if diff1 <= diff2:
                    # If difference1 is smallest, choose first team1
                    team1 = _t1_1
                else:
                    # Otherwise choose second team1
                    team1 = _t1_2
            
            else:              
                team1 = combs[int(middle)]   
        
        else:
            # If teams are uneven, stack the biggest team with the worst players
            # Lazy implementation for now
            team1 = combs[0]
        
        # Team2 is generated from set difference of all players and team1
        team2 = list(set(players_ratings) - set(team1))

        async def calc_team_rating(team: list) -> Tuple[float, str]:
            team_rating = 0
            _team_names = []
            for player in team:
                name, rating, wins, losses = player
                _team_names.append(f"{name.capitalize()} ({round(rating*40)})")
                team_rating += rating*40
            team_rating = team_rating/len(team)
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
        msg += f"Team 1: {team1_names}{t1_spaces}\t+{team1_win}/-{team1_loss}\tAverage rating: {round(team1_rating)}\n"
        msg += f"Team 2: {team2_names}{t2_spaces}\t+{team2_win}/-{team2_loss}\tAverage rating: {round(team2_rating)}\n"
        msg += "```"
        await ctx.send(msg)