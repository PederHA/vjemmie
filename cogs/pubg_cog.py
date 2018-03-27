from discord.ext import commands
import discord
from ext_module import ExtModule
import random
import numpy


class PUBGCog:
    """PUBG Bot Commands
    """

    def __init__(self, bot: commands.Bot, log_channel_id: int=None):
        self.bot = bot
        self.log_channel_id = log_channel_id
        self.send_log = None                # will be assigned

    async def on_ready(self):
        """Is called when the bot is completely started up. Calls in this function need variables only a started bot can give.
        """
        self.send_log = ExtModule.get_send_log(self)

    @commands.command(name='drop',
                      aliases=['roulette', 'plane'],
                      description='u fucking wot')
    async def drop(self, ctx: commands.Context, *args):
        MIRAMAR_LOCATIONS_ALL = ["El Pozo", "Pecado", "Monte Nuevo", "San Martín",
                                 "Hacienda del Patrón", "El Azahar", "Cruz del Valle",
                                 "Tierra Bronca", "Torre Ahumada", "Campo Militar", "Impala",
                                 "La Cobrería", "Los Leones"]

        MIRAMAR_LOCATIONS_HOT = ["El Pozo", "Pecado", "San Martín",
                                 "Hacienda del Patrón", "Campo Militar", "Los Leones"]

        ERANGEL_LOCATIONS_ALL = ["South George", "North George", "Yasnaya",
                                 "School", "Pochinki", "Mylta", "Mylta Power",
                                 "Military Base", "Novorepnoye", "Lipovka", "Prison",
                                 "Shelter", "Primorsk", "Gatka", "Zharki"]

        ERANGEL_LOCATIONS_HOT = ["South George", "North George", "Yasnaya",
                                 "School", "Pochinki", "Mylta", "Mylta Power",
                                 "Military Base", "Novorepnoye"]

        VALID_MAPS = ["Erangel", "Miramar"]
        
        # Only proceed if an argument is given.
        if args != ():  

            pubgmap = args[0].lower()
            pubgmap = pubgmap[0:].capitalize()
            # TODO: 'hot' check and its associated error message should only have to be done once.

            # Check if arg is a valid pubg map
            if pubgmap in VALID_MAPS:
                if pubgmap == 'Miramar':
                    if len(args) > 1:
                        # If the second argument is 'hot', pick location from hot list.
                        if args[1] == 'hot':
                            droplocation = random.choice(MIRAMAR_LOCATIONS_HOT)
                        else:
                            await ctx.send("Invalid arguments. Syntax: \"!drop map (hot)\"")
                    else:
                        droplocation = random.choice(MIRAMAR_LOCATIONS_ALL)

                elif pubgmap == 'Erangel':
                    if len(args) > 1:
                        if args[1] == 'hot':
                            droplocation = random.choice(ERANGEL_LOCATIONS_HOT)
                        else:
                            await ctx.send("Invalid arguments. Syntax: \"!drop map (hot)\"")
                    else:
                        droplocation = random.choice(ERANGEL_LOCATIONS_ALL)

                await ctx.send("Drop location: " + droplocation)

            else:
                await ctx.send(pubgmap[0:].capitalize() + " is not a valid map."
                                "\nMaps currently in the pool are: " + (str(VALID_MAPS)[1:-1]).replace("'", ""))
        # TODO Don't hardcode this error message. Allow for maps to be added to the pool without having to come back to this message.
        else:
            await ctx.send("No map specified. Type \"!drop erangel (hot)\" or \"!drop miramar (hot)\".")

    @commands.command(name='crate',
                      aliases=['crateplay', 'dibs'],
                      description='nah mate ur not getting the awm')
    # TODO: weighted random
    #       Sort list if using numbers
    #       Auto or snipers only
    async def crate(self, ctx: commands.Context, *args):
        CRATEGUNS_ALL = ["M249", "M24", "AWM", "AUG", "Groza", "MK14"]
        CRATEGUNS_NO_M249 = ["M24", "AWM", "AUG", "Groza", "MK14"]
        #crateguns_snipers=["M24", "AWM", "MK14"]
        #crateguns_auto=["M249", "AUG", "Groza"]

        # This whole clusterfuck needs a re-do
        # TODO: Move to function
        if (args == ()) or (len(args) == 1 and args[0] == "m249"):
            squad = ('simon', 'hugo', 'travis', 'steve')
        elif args[0] == '2':
            squad = ('1', '2')
        elif args[0] == '3':
            squad = ('1', '2', '3')
        elif args[0] == '4':
            squad = ('1', '2', '3', '4')
        elif ((len(args) > 4) and ("m249" not in args)) or ((len(args)>5) and ("m249" in args)):
            squad = args
            await ctx.send("How many god damn members do you think can fit in a team?")
        else:
            squad = args

        # Just a little catch-all tuple->list thing
        squad = list(squad)
        
        # Temporary
        if "rad" in squad:
            await ctx.message.add_reaction(':8xscope:417396529452810241')
        
        # Move this check its own function
        if "m249" in args:
            m249 = True
            if "m249" in squad:
                squad.remove("m249")
        else:
            m249 = False

        squadsize = len(squad)
        
        if (squadsize > 1) and (squadsize <= 4):
            random.shuffle(squad)
            # USING NUMPY - SPLIT LIST INTO N PARTS.
            if m249:
                # Shuffle list of crateguns, then split into number of parts equal to squadsize
                random.shuffle(CRATEGUNS_ALL)
                gunsplit = numpy.array_split(CRATEGUNS_ALL, squadsize)

                # If one of the gunsplit indices is  ['M249']: do a reroll
                # TODO: M249-ONLY tag that disables rerolling.
                for n in range(squadsize):
                    gun = gunsplit[n].tolist()
                    while gun == ['M249']:
                        random.shuffle(CRATEGUNS_ALL)
                        gunsplit = numpy.array_split(CRATEGUNS_ALL, squadsize)
                        for g in range(squadsize):
                            gun = gunsplit[g].tolist()
            else:
                random.shuffle(CRATEGUNS_NO_M249)
                gunsplit = numpy.array_split(CRATEGUNS_NO_M249, squadsize)

            # Generate discord bot output
            output = "```"
            for n in range(squadsize):
                linebuffer = ""
                linebuffer = (str(squad[n])[0:].capitalize(
                ) + ": " + str(gunsplit[n])[1:-1].replace("'", "") + "\n")
                output += linebuffer
                n += 1
            output += "```"

            await ctx.send(output)

