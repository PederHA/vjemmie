import asyncio
import math
import sqlite3

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
    async def leaderboard(self, ctx: commands.Context, game="legiontd", alias: bool=False) -> None:
        players = self.db.get_players(game, alias=alias)
        output = "```\nDGVGK Legion TD Rankings:\n\n"
        for player in players:
            name, rating, wins, losses = player
            if len(name) > 10:
                name = name[:10]
            spc = ""
            _spc = 10 - len(name)
            for i in range(_spc):
                spc+=" "
            output += f"{name.capitalize()}{spc}\tRating: {round(rating*40)}\tWins: {wins}\tLosses: {losses}\n"
        else:
            output += "```"
            await ctx.send(output)
        
    
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
        winners_new, losers_new = trueskill.rate([tuple(ts_winners), tuple(ts_losers)])
        
        # Update ratings in DB and generate Discord message
        msg = "```Rating change:\n\n"
        for idx, winner in enumerate(winners_new):
            self.db.update_rating(winners_names[idx], winner, win=True, game=game)
            rating_gain = round((winner.mu - ts_winners[0].mu)*40)
            msg += f"{winners[idx][0].capitalize()}: +{rating_gain} rating.\n"
        for idx, loser in enumerate(losers_new):
            self.db.update_rating(losers_names[idx], loser, win=False, game=game)
            rating_loss = round((ts_losers[0].mu - loser.mu)*40)
            msg += f"{losers[idx][0].capitalize()}: -{rating_loss} rating.\n"   
        msg += "```"
        await ctx.send(msg)

        # Post leaderboard after reporting individual rating changes
        cmd = self.bot.get_command("leaderboard")
        await ctx.invoke(cmd, game)

    @commands.command(name="teams")
    async def autobalance(self, ctx: commands.Context, players: str=None, game: str="legiontd") -> None:
        """
        Distributes `players` to 2 teams based on their rating.

        """

        help_str = """Usage: !teams "player1 player2 player3 player4" (opt: <game>)
                      If command is called without arguments, pulls players from 
                      message author's voice channel."""
        
        if players is None or players == "c":
            # Get players from author's voice channel if no `players` argument is given
            players = await self.get_users_in_voice(ctx)
        else:
            # Create list from string of names separated by spaces
            players = players.split(" ")
        
        try:
            db_players = self.db.get_players(game)
        except sqlite3.OperationalError:
            await ctx.send(f"Could not find player stats for game **{game}**.")
            raise Exception
        
        players_ratings = []
        for db_player in db_players:
            name, rating, wins, losses = db_player
            for player in players:
                if name == player:
                    players_ratings.append(db_player)
                    break
        
        if len(players) % 2 == 0:
            # If n players is even number, select every 2nd player in sorted list players_ratings
            team1 = players_ratings[::2]
        else:
            # If teams are uneven, put highest rated players on the smaller team
            _t1 = math.ceil(len(players) / 2)
            team1 = players_ratings[:_t1]
        team2 = list(set(players_ratings) - set(team1))
        
        team1_rating = 0
        _t1_names = []
        for player in team1:
            name, rating, wins, losses = player
            _t1_names.append(f"{name.capitalize()} ({int(rating*40)})")
            team1_rating += rating*40
        team1_rating = team1_rating/len(team1)
        team1_names = ", ".join(_t1_names)

        team2_rating = 0
        _t2_names = []
        for player in team2:
            name, rating, wins, losses = player
            _t2_names.append(f"{name.capitalize()} ({int(rating*40)})")
            team2_rating += rating*40
        team2_rating = team2_rating/len(team2)
        team2_names = ", ".join(_t2_names)

        t1_spaces = " "*(40-len(team1_names))
        t2_spaces = " "*(40-len(team2_names))

        msg = "```"
        msg += f"Team 1: {team1_names}{t1_spaces} Average rating: {team1_rating}\n"
        msg += f"Team 2: {team2_names}{t2_spaces} Average rating: {team2_rating}\n"
        msg += "```"
        await ctx.send(msg)