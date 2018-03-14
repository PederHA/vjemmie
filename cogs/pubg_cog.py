from discord.ext import commands
import discord
from ext_module import ExtModule
import random
import numpy

import traceback

class PUBGCog:
    """PUBG Bot Commands
    """
    def __init__(self, bot: commands.Bot, log_channel_id: int=None):
        """The constructor of the UserCog class, assigns the important variables
        Args:
            bot: The bot the commands will be added to (commands.Bot)
            log_channel_id: The id of the log_channel (int)
        """
        self.bot = bot
        self.log_channel_id = log_channel_id
        self.send_log = None                # will be assigned
        self.bot.remove_command('help')
    
    async def on_ready(self):
        """Is called when the bot is completely started up. Calls in this function need variables only a started bot can give.
        """
        self.send_log = ExtModule.get_send_log(self)
    
    @commands.command(name='drop',
                        aliases=['roulette', 'plane'],
                        description='(textblock) || u fucking wot')

    @ExtModule.reaction_respond
    async def drop(self, ctx: commands.Context, *args):
        miramar_locations_all = ["El Pozo", "Pecado", "Monte Nuevo", "San Martín",
                                "Hacienda del Patrón", "El Azahar", "Cruz del Valle",
                                "Tierra Bronca", "Torre Ahumada", "Campo Militar", "Impala",
                                "La Cobrería", "Los Leones"]
        
        miramar_locations_hot = ["El Pozo", "Pecado", "San Martín",
                                "Hacienda del Patrón", "Campo Militar", "Los Leones"]

        erangel_locations_all = ["South George", "North George", "Yasnaya",
                                "School", "Pochinki", "Mylta", "Mylta Power", 
                                "Military Base", "Novorepnoye", "Lipovka", "Prison",
                                "Shelter", "Primorsk", "Gatka", "Zharki"]
        
        erangel_locations_hot = ["South George", "North George", "Yasnaya",
                                "School", "Pochinki", "Mylta", "Mylta Power", 
                                "Military Base", "Novorepnoye"]
        
        valid_maps = ["erangel", "miramar"]


        if args != (): #Only proceed if an arg is present.
            
            pubgmap = args[0]
            pubgmap = pubgmap.lower()

            if pubgmap in valid_maps: #Check if supplied arg is a valid pubg map
            #TODO: Don't hardcode map names. Instead take from valid map list.
                if pubgmap == 'miramar':
                    if len(args)>1:
                        if args[1] == 'hot': #If the second argument is 'hot', choose from hot list.
                            droplocation = random.choice(miramar_locations_hot)
                        else:
                            await ctx.send("Invalid arguments. Syntax: \"!drop map (hot)\"")            
                    else:
                        droplocation = random.choice(miramar_locations_all)
                    
                elif pubgmap == 'erangel':
                    if len(args)>1:
                        if args[1] == 'hot':
                            droplocation = random.choice(erangel_locations_hot)
                        else:
                            await ctx.send("Invalid arguments. Syntax: \"!drop map (hot)\"")            
                    else:
                        droplocation = random.choice(erangel_locations_all)

                await ctx.send("Drop location: " + droplocation)
            
            else:
                    await ctx.send(args[0] + " is not a valid map") 
        else: #TODO add for-loop so map list is cycled through and added to this output, instead of hardcoding error message.
            await ctx.send("No map specified. Type \"!drop erangel (hot)\" or \"!drop miramar (hot)\".")

    @commands.command(name='crate',
                        aliases=['crateplay', 'dibs'],
                        description='nah mate ur not getting the awm')
                        
    #THIS IS AN ACTUAL CLUSTERFUCK. How to fix: 
    #if m249 in "squad":
    #squad.remove("m249")
    #squadsize = squadsize - 1
    #gunlist = crateguns_all
    
    
    #TODO: weighted random
    #      Sort list if using numbers

    async def crate(self, ctx: commands.Context, *args):
        crateguns_all=["M249", "M24", "AWM", "AUG", "Groza", "MK14"]
        crateguns_nom249=["M24", "AWM", "AUG", "Groza", "MK14"]
        #crateguns_snipers=["M24", "AWM", "MK14"]
        #crateguns_auto=["M249", "AUG", "Groza"]
        #user_args = args
        print(args)

        #TODO: Change variable names. FIX m249 for numbers
        #if (len(args) != 1) or (args == ('m249',)):
        if (args == ()) or (len(args)==1 and args[0] == "m249"):
            squad = ('simon', 'hugo', 'travis', 'steve')
        elif args[0] == '2':
            squad = ('1','2')
        elif args[0] == '3':
            squad = ('1','2','3')
        elif args[0] == '4':
            squad = ('1','2','3','4')
        elif (len(args)>4) and ("m249" not in args):
            squad = args
            await ctx.send("How many god damn members do you think can fit in a team?")
        else:
            squad = args
        #squad = args
        squad = list(squad)
        args = list(args)
        #m249 isnt in squad cause it gets its value from args, which is overwritten
        if "m249" in args:
            m249 = True
            args.remove("m249")
        else:
            m249 = False
        
        squadsize = len(squad)
        print ("Squadsize = ", squadsize)
        
        print(m249)
        if (squadsize > 1) and (squadsize <= 4):


            random.shuffle(squad)
            
            #USING NUMPY - SPLIT LIST INTO N PARTS.
            if m249 == True:
                #Shuffle list of crateguns, then split into number of parts equal to squadsize
                random.shuffle(crateguns_all)
                gunsplit = numpy.array_split(crateguns_all,squadsize)
                
                #If one of the gunsplit indices is only ['M249']: do a reroll
                for n in range(squadsize):
                    gun = gunsplit[n].tolist()
                    while gun == ['M249']:
                        random.shuffle(crateguns_all)
                        gunsplit = numpy.array_split(crateguns_all,squadsize)
                        for g in range(squadsize):
                            gun = gunsplit[g].tolist()
            else:
                random.shuffle(crateguns_nom249)
                gunsplit = numpy.array_split(crateguns_nom249,squadsize)

            output = "```"
            for n in range(squadsize):
                linebuffer = ""
                linebuffer = (str(squad[n])[0:].capitalize() + ": " + str(gunsplit[n])[1:-1].replace("'","") + "\n")
                output += linebuffer
                n+=1
            output += "```"

            await ctx.send(output)


    @commands.command(name='roll',
                        aliases=['dice'],
                        description='Random roll. Provide number argument to specify range (1-100 default).')
    
    async def roll(self, ctx: commands.Context, *args):
        """Code created while sleep deprived. High chance of being utter shit.
            The rolling() method used to make sense before i rewrote the roll() method.
            Now it's sort of pointless, really.
        """
        async def rolling(lower: int, upper: int):
            #For good measure, random number variable is initialized to 0.
            random_number = 0
            
            random_number = random.randint(lower,upper)
            return random_number   
        
        #Default values
        random_range_lower = 1
        random_range_upper = 100
        
        try:
            if len(args) == 1:
                #If 1 argument is provided, the upper range is changed to the user defined value.
                random_range_upper = int(args[0])
            elif len(args) > 1:
                #If 2 (or more) arguments are provided, the 1st and 2nd indices of the args tuple are cast to integers.    
                random_range_lower = int(args[0])
                random_range_upper = int(args[1])
            
            #This block of shit needs some cleaning up. Probably don't need the type check when catching exceptions below.
            if (isinstance(random_range_lower, int)) and (isinstance(random_range_upper, int)):
                rollresult = await rolling(random_range_lower,random_range_upper)
                random_range_lower = str(random_range_lower)
                random_range_upper = str(random_range_upper)
                random_number = str(rollresult)
                await ctx.send("Rolling " + random_range_lower + " - " + random_range_upper  + ": " 
                                + "  **" + random_number + "**")
        
        #Manually catch the two common exceptions that can occur + unknown exception.
        except ValueError:
            error = traceback.format_exc()
            if "invalid literal" in error:
                #Invalid literal error stems from 1 or more args not being integers
                await ctx.send("Only numbers are accepted. You utter, utter retard.")   
            elif "empty range" in error:
                #Empty range exception stems from random_range_lower being greater than random_range_upper.
                await ctx.send("An error occured. The first value should be less or equal to the second value.")
            else:
                await ctx.send("An unknown error occured. You probably fucked something up.")
