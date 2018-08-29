from discord.ext import commands
import discord
from ext_module import ExtModule
import random
import numpy
from events_module import EventsModule
from bot_resources import GUILDS, NON_PUBG_PLAYERS
from utils.ext_utils import is_int


class PUBGCog:
    """PUBG Bot Commands
    """

    def __init__(self, bot: commands.Bot, log_channel_id: int = None):
        self.bot = bot
        self.log_channel_id = log_channel_id
        self.send_log = None

    async def on_ready(self):
        self.send_log = ExtModule.get_send_log(self)

    @commands.command(
        name="drop", aliases=["roulette", "plane"], description="u fucking wot"
    )
    async def drop(self, ctx: commands.Context, *args):
        """
        ``!drop``command that chooses random drop location on a given PUBG map.
        ----
        
        Args: tuple containing user arguments provided after typing !drop.
        """

        MIRAMAR_LOCATIONS_ALL = [
            "El Pozo",
            "Pecado",
            "San Martín",
            "Hacienda del Patrón",
            "Campo Militar",
            "Los Leones",
            "Monte Nuevo",
            "El Azahar",
            "Cruz del Valle",
            "Tierra Bronca",
            "Torre Ahumada",
            "Impala",
            "La Cobrería",
        ]

        MIRAMAR_LOCATIONS_HOT = MIRAMAR_LOCATIONS_ALL[:6]

        ERANGEL_LOCATIONS_ALL = [
            "South George",
            "North George",
            "Yasnaya",
            "School",
            "Pochinki",
            "Mylta",
            "Mylta Power",
            "Military Base",
            "Novorepnoye",
            "Lipovka",
            "Prison",
            "Shelter",
            "Primorsk",
            "Gatka",
            "Zharki",
        ]

        ERANGEL_LOCATIONS_HOT = ERANGEL_LOCATIONS_ALL[:9]

        VALID_MAPS = ["Erangel", "Miramar"]
        invalid_args_msg = 'Invalid arguments. Syntax: "!drop <map> (hot)"'
        invalid_map = False
        no_map = False

        # Only valid_args if an argument is given.
        if args != ():

            pubgmap = args[0].lower()
            pubgmap = pubgmap[0:].capitalize()

            # Check if arg is a valid pubg map
            if pubgmap in VALID_MAPS:
                if pubgmap == "Miramar":
                    if len(args) > 1:
                        # If the second argument is 'hot', pick location from hot list.
                        if args[1] == "hot":
                            droplocation = random.choice(MIRAMAR_LOCATIONS_HOT)
                        else:
                            await ctx.send(invalid_args_msg)
                    else:
                        droplocation = random.choice(MIRAMAR_LOCATIONS_ALL)

                elif pubgmap == "Erangel":
                    if len(args) > 1:
                        if args[1] == "hot":
                            droplocation = random.choice(ERANGEL_LOCATIONS_HOT)
                        else:
                            await ctx.send(invalid_args_msg)
                    else:
                        droplocation = random.choice(ERANGEL_LOCATIONS_ALL)

                await ctx.send("Drop location: " + droplocation)

            else:
                invalid_map = True

        else:
            no_map = True
        
        if no_map or invalid_map:
            if no_map:
                message = "No map specified. Type "
            if invalid_map:
                message = "Invalid map specified. Type "
            
            first_map = True
            for pubgmap in VALID_MAPS:
                if not first_map:
                    message += " or "
                message+= f"`!drop {pubgmap} (hot)`"
                first_map = False
            else:
                message += "."
            await ctx.send(message)


    # Start of Crate command
    @commands.command(
        name="crate",
        aliases=["crateplay", "dibs"],
        description="nah mate ur not getting the awm",
    )
    async def crate(self, ctx: commands.Context, *args):
        """
        Distributes potential weapons found in PUBG airdrops among
        `args` number of players. 
        
        `args` can be a tuple containing
        multiple strings, each representing a squad member, or a 
        tuple containing a single string representing the number
        of squad members.
        """

        enough_players = True
        bot_msg = ""
        default_squad = ("simon", "hugo", "travis", "steve")

        if args == ():
            squad = default_squad
        elif args[0].isdigit():
            number_of_players = int(args[0])
            if 1 < number_of_players <= 4:
                int_list = list(range(number_of_players + 1))
                int_list = int_list[1:]
                squad_list = []
                for n in int_list:
                    n = str(n)
                    squad_list.append(n)
                squad = squad_list
            elif number_of_players > 4:
                bot_msg = "Can't roll crate for more than 4 players."
            else:
                bot_msg = "The specified range is too low. 2-4 players are needed."
        elif args[0] in ["channel", "c", "ch", "chanel"]:
            squad = await self.get_squad_from_channel(ctx)
            if len(squad)==0:    
                bot_msg = "Must be connected to a voice channel to use <channel> argument."
            elif len(squad)==1:
                bot_msg = "Only 1 user is connected to the voice channel. Crate cannot be rolled."
        elif len(args) == 1:
            bot_msg = "Can't roll crate for 1 player."
        else:
            squad = args
        
        if bot_msg != "":
            enough_players = False # If any `bot_msg` is specified, command will exit.

        if not enough_players:
            await ctx.send(bot_msg)

        else:
            # Create a list from the `*args`` tuple to make it mutable.
            squad = list(squad)

            if EventsModule.contains_rad(squad):
                await ctx.message.add_reaction(":8xscope:417396529452810241")

            # Determines size of squad and distributes guns accordingly.
            # Returns size of squad and gun list containing n=squadsize lists.
            gunsplit, armorsplit = await self.roll_guns(squad)
            output = await self.generate_crate_text(squad, gunsplit, armorsplit)

            await ctx.send(output)

    async def roll_guns(self, squad):
        _CRATEGUNS_ALL = [
            "AWM",
            "AUG",
            "Groza",
            "MK14",
            "Ghillie",
            "Helm",
            "Vest",
            "M249",
        ]
        GUNS = _CRATEGUNS_ALL[:4]
        EQUIPMENT = _CRATEGUNS_ALL[4:]

        # Shuffle lists
        random.shuffle(squad)
        random.shuffle(GUNS)
        random.shuffle(EQUIPMENT)

        # Divide lists by len(squad)
        squadsize = len(squad)

        gunsplit = numpy.array_split(GUNS, squadsize)
        random.shuffle(gunsplit)

        armorsplit = numpy.array_split(EQUIPMENT, squadsize)

        # Reroll if one person gets 4 items in a 3-man squad.
        if squadsize == 3:
            for n in range(squadsize):
                while len(gunsplit[n]) == 2 and len(armorsplit[n]) == 2:
                    random.shuffle(gunsplit)
                    random.shuffle(armorsplit)

        return gunsplit, armorsplit

    async def generate_crate_text(self, squad, gunsplit, armorsplit):
        squadsize = len(squad)
        


        # Generate discord bot output
        output = "```"        
        if squad[0].isdigit(): 
            # Sort squad numerically
            squad.sort() 
        
        for n in range(squadsize):    
            # Create string object from list index
            squad_member = squad[n] 
            
            if squad_member.islower():
                squad_member = squad_member.capitalize()

            gun = str(gunsplit[n])[1:-1].replace("'", "")
            equipment = str(armorsplit[n])[1:-1].replace("'", "")
            text_line = ""
            text_line = f"{squad_member}: " f"{gun} " f"{equipment}\n"
            output += text_line
        
        output += "```"
        return output

    async def get_squad_from_channel(self, ctx):
        """
        Instead of using a non-PUBG player blacklist
        it is possible to use `member.activity`. 
        However, since not everyone has game activity
        enabled, this would prove to be unreliable.
        """

        squad_list = []
        try:
            for member in ctx.message.author.voice.channel.members:
                if not member.voice.self_deaf:
                    if member.id not in NON_PUBG_PLAYERS:
                        if member.nick != None:
                            squad_list.append(member.nick)
                        else:
                            squad_list.append(member.name)
        except AttributeError:
            pass # This error will be handled by `crate` method.
        
        return squad_list

        
