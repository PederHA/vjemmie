from discord.ext import commands
import discord
from ext_module import ExtModule
import random
import numpy
from events_module import EventsModule
from bot_resources import GUILDS, NON_PUBG_PLAYERS


class PUBGCog:
    """PUBG Bot Commands
    """

    def __init__(self, bot: commands.Bot, log_channel_id: int = None):
        self.bot = bot
        self.log_channel_id = log_channel_id
        self.send_log = None  # will be assigned

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

        # Only valid_args if an argument is given.
        if args != ():

            pubgmap = args[0].lower()
            pubgmap = pubgmap[0:].capitalize()
            # TODO: 'hot' check and its associated error message should only have to be done once.

            # Check if arg is a valid pubg map
            if pubgmap in VALID_MAPS:
                if pubgmap == "Miramar":
                    if len(args) > 1:
                        # If the second argument is 'hot', pick location from hot list.
                        if args[1] == "hot":
                            droplocation = random.choice(MIRAMAR_LOCATIONS_HOT)
                        else:
                            await ctx.send(
                                'Invalid arguments. Syntax: "!drop map (hot)"'
                            )
                    else:
                        droplocation = random.choice(MIRAMAR_LOCATIONS_ALL)

                elif pubgmap == "Erangel":
                    if len(args) > 1:
                        if args[1] == "hot":
                            droplocation = random.choice(ERANGEL_LOCATIONS_HOT)
                        else:
                            await ctx.send(
                                'Invalid arguments. Syntax: "!drop map (hot)"'
                            )
                    else:
                        droplocation = random.choice(ERANGEL_LOCATIONS_ALL)

                await ctx.send("Drop location: " + droplocation)

            else:
                await ctx.send(
                    pubgmap[0:].capitalize() + " is not a valid map."
                    "\nMaps currently in the pool are: "
                    + (str(VALID_MAPS)[1:-1]).replace("'", "")
                )
        # TODO Don't hardcode this error message. Allow for maps to be added to the pool without having to come back to this message.
        else:
            await ctx.send(
                'No map specified. Type "!drop erangel (hot)" or "!drop miramar (hot)".'
            )

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

        valid_args = True

        if (args == ()) or (len(args) == 1 and args[0] == "m249"):
            squad = ("simon", "hugo", "travis", "steve")
        elif args[0] == "2":
            squad = ("1", "2")
        elif args[0] == "3":
            squad = ("1", "2", "3")
        elif args[0] == "4":
            squad = ("1", "2", "3", "4")
        elif args[0] in ["channel", "c", "ch", "chanel"]:
            squad = await self.get_squad_from_channel(ctx)
        elif len(args) == 1:
            await ctx.send("Can't roll crate for 1 player.")
            valid_args = False
        else:
            squad = args

        if valid_args and squad != None:
            # Create a list from the *args tuple, to make it mutable.
            squad = list(squad)

            # Temporary
            if EventsModule.contains_rad(squad):
                await ctx.message.add_reaction(":8xscope:417396529452810241")

            # Determines size of squad and distributes guns accordingly.
            # Returns size of squad and gun list containing n=squadsize lists.
            gunsplit, armorsplit = await self.roll_guns(squad)
            output = await self.generate_crate_text(squad, gunsplit, armorsplit)

            await ctx.send(output)

        if squad == None:
            await ctx.send("Cannot find channel members to roll crate for.")

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
        try:
            try_int = int(squad[0])
            is_int = True
        except:
            is_int = False

        # Generate discord bot output
        output = "```"
        for n in range(squadsize):
            if is_int:
                squad.sort()
            squad_member = str(squad[n])[0:].capitalize()
            gun = str(gunsplit[n])[1:-1].replace("'", "")
            equipment = str(armorsplit[n])[1:-1].replace("'", "")
            text_line = ""
            text_line = f"{squad_member}: " f"{gun} " f"{equipment}\n"
            output += text_line
        output += "```"
        return output

    async def get_squad_from_channel(self, ctx):
        for guild_id in GUILDS:
            guild = self.bot.get_guild(guild_id)
            squad_list = []
            for voice_channel in guild.voice_channels:
                for member in voice_channel.members:
                    if member.id == ctx.message.author.id:
                        author_voice_channel = voice_channel
                        for member in author_voice_channel.members:
                            if member.id not in NON_PUBG_PLAYERS:
                                if member.nick != None:
                                    squad_list.append(member.nick)
                                else:
                                    squad_list.append(member.name)
                            return squad_list
