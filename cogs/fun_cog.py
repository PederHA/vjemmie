from discord.ext import commands
import discord
from ext_module import ExtModule
import random
import traceback
import asyncio
from gtts import gTTS
from cogs.sound_cog import SoundboardCog


class FunCog:
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
    async def roll2(self, ctx: commands.Context, *args):
        """Basically https://xkcd.com/221/.
        """
        async def roll_names(names):
            
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
        else:
            if len(args) == 0:
                error_amount = "No arguments"
            else:
                error_amount = "Only **1** argument was"
            
            await ctx.send(("{} provided. Type **!random** followed by at least 2 words.").format(error_amount))
    




        

