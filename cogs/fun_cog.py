from discord.ext import commands
import discord
from ext_module import ExtModule
import random
import traceback

class FunCog:
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
           
    @commands.command(name='roll',
                      aliases=['dice'],
                      description='Random roll. Provide number argument to specify range (1-100 default).')
    async def roll(self, ctx: commands.Context, *args):
        """Code written while sleep deprived. High chance of being utter shit.
            The rolling() method used to make sense before i rewrote the roll() method.
            Now it's sort of pointless, really.
        """
        async def rolling(lower: int, upper: int):
            random_number = 0

            random_number = random.randint(lower, upper)
            return random_number

        # Default values
        random_range_lower = 1
        random_range_upper = 100

        try:
            if len(args) == 1:
                # If 1 argument is provided, the upper range is changed to the user defined value.
                random_range_upper = int(args[0])
            elif len(args) > 1:
                # If 2 (or more) arguments are provided, the 1st and 2nd indices of the args tuple are cast to integers.
                random_range_lower = int(args[0])
                random_range_upper = int(args[1])

            # This block of shit needs some cleaning up. Probably don't need the type check when catching exceptions below.
            if (isinstance(random_range_lower, int)) and (isinstance(random_range_upper, int)):
                rollresult = await rolling(random_range_lower, random_range_upper)
                random_range_lower = str(random_range_lower)
                random_range_upper = str(random_range_upper)
                random_number = str(rollresult)
                await ctx.send("Rolling " + random_range_lower + " - " + random_range_upper + ": "
                               + "  **" + random_number + "**")

        # Manually catch the two common exceptions that can occur + unknown exception.
        except ValueError:
            error = traceback.format_exc()
            if "invalid literal" in error:
                # Invalid literal error stems from 1 or more args not being integers
                await ctx.send("Only integers are allowed. You utter, utter retard.")
            elif "empty range" in error:
                # Empty range exception stems from random_range_lower being greater than random_range_upper.
                await ctx.send("An error occured. The first value should be less or equal to the second value.")
            else:
                await ctx.send("An unknown error occured. You probably fucked something up.")