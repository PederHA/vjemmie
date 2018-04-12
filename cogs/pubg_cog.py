from discord.ext import commands
import discord
from ext_module import ExtModule
import random
import numpy
from events_module import EventsModule

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
        """
        ``!drop``command that chooses random drop location on a given PUBG map.
        ----
        
        Args: tuple containing user arguments provided after typing !drop.
        """

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
    
    # Start of Crate command
    @commands.command(name='crate',
                      aliases=['crateplay', 'dibs'],
                      description='nah mate ur not getting the awm')
    async def crate(self, ctx: commands.Context, *args):
        """
        Distributes potential weapons found in PUBG airdrops among
        `args` number of players. 
        
        `args` can be a tuple containing
        multiple strings, each representing a squad member, or a 
        tuple containing a single string representing the number
        of squad members.
        """

        # This whole clusterfuck needs a re-do
        # TODO: Move to function
        if (args == ()) or (len(args) == 1 and args[0] == "m249"):
            squad = ('simon', 'hugo', 'travis', 'steve')
        elif args[0] == "2":
            squad = ("1", "2")
        elif args[0] == "3":
            squad = ("1", "2", "3")
        elif args[0] == "4":
            squad = ("1", "2", "3", "4")
        elif ((len(args) > 4) and ("m249" not in args)) or ((len(args)>5) and ("m249" in args)):
            squad = args
            await ctx.send("How many god damn members do you think can fit in a team?")
        elif (len(args) == 2 and "m249" in args):
            await ctx.send("Can't roll crate for 1 player.")
        else:
            squad = args

        # Create a list out of the args tuple, so it can be modified.
        squad = list(squad)
        
        # Temporary
        if EventsModule.contains_rad(squad):
            await ctx.message.add_reaction(':8xscope:417396529452810241')

        # Determines size of squad and distributes guns accordingly.
        # Returns size of squad and gun list containing n=squadsize lists.
        squadsize, gunsplit = await self.roll_guns(args,squad)
        output = await self.generate_crate_text(squadsize,squad,gunsplit)
        
        await ctx.send(output)
    
    async def roll_guns(self, args, squad):
        CRATEGUNS_ALL = ["M249", "M24", "AWM", "AUG", "Groza", "MK14", "Ghillie"]
        CRATEGUNS_NO_M249 = ["M24", "AWM", "AUG", "Groza", "MK14", "Ghillie"]
        SOLO_ROLL_BLACKLIST = ["M249", "Ghillie"] #NYI
        #crateguns_snipers=["M24", "AWM", "MK14"]
        #crateguns_auto=["M249", "AUG", "Groza"]
        
        m249, squad = await self.check_m249(args,squad)

        squadsize = len(squad)

        if (squadsize > 1) and (squadsize <= 4):
            random.shuffle(squad)
            
            if m249:
                gunlist = CRATEGUNS_ALL
            else:
                gunlist = CRATEGUNS_NO_M249

            # Shuffle list of crateguns, then split into number of parts equal to squadsize
            random.shuffle(gunlist)
            # using numpy split list into n=len(squad) parts.
            gunsplit = numpy.array_split(gunlist, squadsize)
            needs_reroll = False

            # Reroll if one of the gunsplit indices is ["M249"] or ["Ghillie"]
            # TODO: M249-ONLY tag that disables rerolling.
            for n in range(squadsize):
                gun = gunsplit[n].tolist()
                if ((gun == ["M249"]) or (gun == ["Ghillie"]) 
                or (("M249" in gun) and ("Ghillie" in gun))):
                    needs_reroll = True
                
                # Not working properly
                while needs_reroll:
                    
                    random.shuffle(gunlist)
                    gunsplit = numpy.array_split(gunlist, squadsize)
                    
                    for g in range(squadsize):
                        gun = gunsplit[g].tolist()
                        if gun == ["Ghillie"] or gun == ["M249"]:
                            needs_reroll = True
                            break
                        
                        # Absolute shitstain of a statement right here. Will change asap.
                        elif ((gun != ["Ghillie"]) or (("Ghillie" in gun) and not gun == ["Ghillie"])
                        or ("M249" in gun) and (not gun == ["M249"]) or ("Ghillie" in gun) and ("M249" in gun)):
                            needs_reroll = False
            
            return squadsize, gunsplit

    async def check_m249(self, args, squad):
        if "m249" in args:
            if "m249" in squad:
                squad.remove("m249")
            return True, squad
        else:
            return False, squad

    async def generate_crate_text(self, squadsize, squad, gunsplit):
        # Generate discord bot output
        output = "```"
        for n in range(squadsize):
            linebuffer = ""
            linebuffer = (str(squad[n])[0:].capitalize(
            ) + ": " + str(gunsplit[n])[1:-1].replace("'", "") + "\n")
            output += linebuffer
            n += 1
        output += "```"
        
        return output
    
    async def split_guns(self, squad, squadsize, m249):
        pass         
    # End of crate command