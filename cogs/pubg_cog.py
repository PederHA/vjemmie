from discord.ext import commands
import discord
from ext_module import ExtModule
import random
import numpy

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
        
        #valid_maps = ["Erangel", "Miramar"]

        #TODO: Fix if-statement so I only need 1 ctx.send instead of 1 for each of the maps

        #THIS IS HORRENDOUS. TO-DO: MAKE FUNCTION FOR INVALID MAP / ARG. FIND A WAY TO CONSOLIDATE THE ARG CHECKS.
        if args != (): #IF A MAP IS SPECIFIED -> ENTER 
            if (args[0] == 'erangel') or (args[0] == 'miramar'): #IF VALID MAPS ARE SPECIFIED. TO-DO: DONT HARD CODE MAP NAMES
                
                if args[0] == 'miramar':
                    if len(args)>1:
                        if args[1] == 'hot':
                            droplocation = random.choice(miramar_locations_hot)
                        else:
                            await ctx.send("Invalid arguments. Syntax: \"!drop <Map> ( + <Hot>)\"")            
                    else:
                        droplocation = random.choice(miramar_locations_all)
                    
                elif args[0] == 'erangel':
                    print ("we r inside erangel")
                    if len(args)>1:
                        if args[1] == 'hot':
                            droplocation = random.choice(erangel_locations_hot)
                        else:
                            await ctx.send("Invalid arguments. Syntax: \"!drop <Map> ( + <Hot>)\"")            
                    else:
                        droplocation = random.choice(erangel_locations_all)

                await ctx.send("Drop location: " + droplocation)
            
            else:
                    await ctx.send(args[0] + " is not a valid map") 
        else:
            await ctx.send("No map specified. Type \"!drop erangel (hot)\" or \"!drop miramar (hot)\".")

    @commands.command(name='crate',
                        aliases=['crateplay', 'dibs'],
                        description='nah mate ur not getting the awm')
    #TODO: weighted random
    
    async def crate(self, ctx: commands.Context, *args):
        crateguns_all=["M249", "M24", "AWM", "AUG", "Groza", "MK14"]
        crateguns_nom249=["M24", "AWM", "AUG", "Groza", "MK14"]
        #crateguns_snipers=["M24", "AWM", "MK14"]
        #crateguns_auto=["M249", "AUG", "Groza"]
        
        if len(args) != 1:
            if args == ():
                args = ('simon', 'hugo', 'travis', 'steve')

            squadsize = len(args)
            squadlist = list(args)
            random.shuffle(squadlist)
            
            #USING NUMPY - SPLIT LIST INTO N PARTS.
            for arg in range (len(args)):
                if args[arg] == "m249": #NON FUNCTIONAL. STUPID SOLUTION ANYWAY.
                    random.shuffle(crateguns_all)
                    gunsplit = numpy.array_split(crateguns_all,squadsize)
                else:
                    random.shuffle(crateguns_nom249)
                    gunsplit = numpy.array_split(crateguns_nom249,squadsize)

            #TODO: Fix m249

            output = "```"
            for n in range(squadsize):
                if squadlist[n] != "m249": #unfinished
                    linebuffer = ""
                    linebuffer = (str(squadlist[n])[0:].capitalize() + ": " + str(gunsplit[n])[1:-1].replace("'","") + "\n")
                    output += linebuffer
                
                else:
                    print ("yeboi")
                n+=1
            output += "```"
            await ctx.send(output)
        else:
            await ctx.send("u fuckin dumb or what")    
            