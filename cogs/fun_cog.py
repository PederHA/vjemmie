import asyncio
import random
import traceback
from pprint import pprint
from secrets import FPL_LEAGUE_ID, REALNAME_ID

import discord
from discord.ext import commands
from fpl import FPL

from cogs.base_cog import BaseCog
from ext_module import ExtModule
from utils.argsparsing import parse_args


class FunCog(BaseCog): 
    @commands.command(name='roll',
                      aliases=['dice'],
                      description='Random roll. Provide number argument to specify range (1-100 default).')
    async def roll(self, ctx: commands.Context, *args):
        """Code written while sleep deprived. High chance of being utter shit.
            The rolling() method used to make sense before i rewrote the roll() method.
            Now it's sort of pointless, really.
        """
        async def roll_numbers(lower: int, upper: int):
            random_number = random.randint(lower, upper)
            return random_number
        
        async def is_number(args):
            try:
                for i in range(len(args)):
                    int(args[i])
                return True
            except ValueError:
                return False
        
        # The is_number method returns True if no arguments are given, since the for-loop is never entered.
        # Which means no exception can occur.
        args_are_ints = await is_number(args)
                    
        # Default values
        random_range_lower = 1
        random_range_upper = 100
        
        if args_are_ints:
            try:
                if len(args) == 1:
                    # If 1 argument is provided, the upper range is changed to the user defined value.
                    random_range_upper = int(args[0])
                elif len(args) > 1:
                    # If 2 (or more) arguments are provided, the 1st and 2nd indices of the args tuple are cast to integers.
                    random_range_lower = int(args[0])
                    random_range_upper = int(args[1])

                rollresult = await roll_numbers(random_range_lower, random_range_upper)
                
                await ctx.send("Rolling " + str(random_range_lower) + " - " + str(random_range_upper) + ": "
                            + "  **" + str(rollresult) + "**")

            # Error messages for invalid order of numbers & unknown exception.
            except:
                error = traceback.format_exc()
                if "empty range" in error:
                    # Empty range exception stems from random_range_lower being greater than random_range_upper.
                    await ctx.send("An error occured. The first value should be less or equal to the second value.")
                else:
                    await ctx.send("An unknown error occured. You probably fucked something up.")
        else:
            await ctx.send("Only integers are allowed you utter, utter retard.")
            
    @commands.command(name='randomchoice',
                      aliases=['random'],
                      description='Random choice of two or more args')
    async def roll2(self, ctx: commands.Context, *args) -> None:
        """
        Basically https://xkcd.com/221/.
        """
        async def roll_names(names: tuple) -> str:           
            # Implemented due to complaints about rigged RNG :thinking:
            for i in range(random.randint(2,5)):
                random_name = random.choice(names)
            return random_name
        
        if args != () and len(args)>1:
            try:
                args = list(args)
                random_name = await roll_names(args)
            # Catch-all bullshit error message.
            except:
                await ctx.send("An error occured.")
            else:
                await ctx.send(random_name[0:].capitalize())
        elif args == ("c",):
            roll_list = await self.get_users_in_voice(ctx)
            if roll_list is not None:
                random_name = await roll_names(roll_list)
                await ctx.send(random_name[0:].capitalize())
        else:
            if len(args) == 0:
                error_amount = "No arguments"
            else:
                error_amount = "Only **1** argument was"
        
            await ctx.send(f"{error_amount} provided. Type `!random` followed by at least 2 words.")
        
    @commands.command(name="fpl")
    async def fantasy_pl(self, ctx: commands.Context, *args) -> None:
        """
        Fantasy Premier League commands. 
        -----
        Only functionality implemented so far is printing the best or
        worst player from the current game week.
        """
        
        TIMEFRAME_ARGS = ["week", "all"]
        FILTERING_ARGS = ["worst", "best"]
        DEBUG_ARGS = ["test", "debug"]
        
        if args == ():
            # Defaults to "week" & "best"
            args = (TIMEFRAME_ARGS[1], FILTERING_ARGS[1])
        if args != ():
            timeframe, filtering = parse_args(args, 2)
            if timeframe in TIMEFRAME_ARGS:
                if filtering == FILTERING_ARGS[1] or filtering == None:
                    returned = await self.fpl_week_points(best=True)
                elif filtering == FILTERING_ARGS[0]:
                    returned = await self.fpl_week_points(best=False)
            # Duplicate code, but will be refactored later
            elif timeframe in DEBUG_ARGS:
                if filtering == "best" or filtering == None:
                    returned = await self.fpl_week_points(best=True, debug=True)
                else:
                    returned = await self.fpl_week_points(best=False, debug=True)
            await ctx.send(returned)
            

    async def fpl_week_points(self, best=True, debug=False) -> str:
        """
        I feel like I shouldn't need to manually access dict keys when using an API
        wrapper, however the `get_standings()` method returned None for me, so here we are.
        """
        if not debug:
            _fpl = FPL()
            league = _fpl.get_classic_league(FPL_LEAGUE_ID)
            league_info = league._get_information()
        
        elif debug:
            # For debugging point tie scenarios
            league_info = {
                "standings": {
                    "results": [
                        {"player_name": list(REALNAME_ID.keys())[0], "event_total": 0},
                        {"player_name": list(REALNAME_ID.keys())[6], "event_total": 1},
                        {"player_name": list(REALNAME_ID.keys())[3], "event_total": 1},
                        {"player_name": list(REALNAME_ID.keys())[1], "event_total": 1},
                    ]
                }
            }
            pprint(league_info)

        score = 0
        players = []
        active_gameweek = False
        point_tie = False
            
        if best:
            filtering = "best"
        else:
            filtering = "worst"        

        try:
            for team in league_info["standings"]["results"]:
                team_score = team["event_total"]
                player_name = team["player_name"]
                
                if team_score == score and score == 0:
                    players.append(player_name)
 
                if team["event_total"] > 0:
                    active_gameweek = True
                
                if best:
                    if team_score > score:
                        score = team_score
                        players = [player_name]
                    elif team_score == score and score != 0:
                        players.append(player_name)  
                else:
                    if team_score < score:
                        score = team_score
                        players = [player_name]
                    elif team_score == score and score != 0:
                        players.append(player_name)
  

        except:
            return "Something went wrong. Try again later."
        
        else:
            if len(players) == 1:
                point_tie = False
            elif len(players) > 1:
                point_tie = True
    
            if debug:
                print(f"players: {players}\nscore: {score}\npoint_tie: {point_tie}")
            
            # Generate discord message
            if not active_gameweek:
                output_msg = "No games have been played yet this week."

            elif not point_tie:
                for k, v in REALNAME_ID.items():
                    if k == players[0]:
                        player = self.bot.get_user(v)
                        player = player.name
                        output_msg = f"The {filtering} player this week is {player} with {score} points!"

            elif point_tie:
                # TODO: Refactor to use the dict builtin method .get()
                player_usernames = []
                for k, v in REALNAME_ID.items():
                    for player in players:
                        if k == player:
                            p_username = self.bot.get_user(v)
                            p_username = p_username.name
                            player_usernames.append(p_username)
                else:
                    fmt_names = ""
                    n = 0
                    for name in player_usernames:
                        n += 1
                        fmt_names += name
                        if len(player_usernames) != n:
                            if len(player_usernames) - n == 1:
                                fmt_names += " and "  
                            else:
                                fmt_names += ", "
                    output_msg = f"The {filtering} players this week are {fmt_names} with {score} points!"
            
            return output_msg

    #@commands.command(name="teams")
    #async def teams(self, ctx: commands.Context, team_size: int=None) -> None:
    #    # Get list of usernames in message author's voice channel
    #    users = get_users_in_author_voice_channel(ctx)
    #
    #    if team_size is None:
    #        team_size = len(users) // 2
    #    else:
    #        # Cast to int to avoid float nums. Raises exception if not a number.
    #        team_size = int(team_size)
    #    
    #    # Raise exception for 99% of user errors and send helpful reply
    #    if len(users) <= 2 or team_size >= len(users):
    #        await ctx.send("you dumb or what")
    #        raise discord.DiscordException
    #
    #    team_1 = random.sample(users, team_size)
    #    team_2 = [user for user in users if user not in team_1]
    #    # Should use regular expressions or smth
    #    team_1 = str(team_1).replace("[", "").replace("]", "").replace("'", "")
    #    team_2 = str(team_2).replace("[", "").replace("]", "").replace("'", "")
    #    await ctx.send(f"**Team 1:** {team_1}.\n**Team 2:** {team_2}")

    #@commands.command(name="teams2")
    #async def teams2(self, ctx: commands.Context, teams: int=2, team_size: int=None) -> None:
    #
    #    # Get list of usernames in message author's voice channel
    #    users = get_users_in_author_voice_channel(ctx)
    #
    #    if team_size is None:
    #        team_size = len(users) // 2
    #    else:
    #        # Cast to int to avoid float nums. Raises exception if not a number.
    #        team_size = int(team_size)
    #    
    #    # Validate team_size and teams
    #    if teams>=len(users):
    #        msg = "Can't have more teams than players."
    #    # Make sure at least 1 team can fill team_size, rest has 1
    #    elif (len(users) / teams + team_size) > len(users):
    #        msg = f"With a team size of {team_size}, unable to fill all teams with at least 1 player."
    #    # Raise exception for 99% of user errors and send helpful reply
    #    elif len(users) <= 2 or team_size >= len(users):
    #        msg = "you dumb or what"
    #    if msg != "":
    #        raise Exception(msg)
    #    
    #    
    #    team_1 = random.sample(users, team_size)
    #    team_2 = [user for user in users if user not in team_1]
    #    # Should use regular expressions or smth
    #    team_1 = str(team_1).replace("[", "").replace("]", "").replace("'", "")
    #    team_2 = str(team_2).replace("[", "").replace("]", "").replace("'", "")
    #    await ctx.send(f"**Team 1:** {team_1}.\n**Team 2:** {team_2}")
