import asyncio
import random
import traceback
from pprint import pprint

import discord
import aiohttp
from discord.ext import commands

from cogs.base_cog import BaseCog
from botsecrets import REMOVEBG_API_KEY


class FunCog(BaseCog): 
    @commands.command(name='roll',
                      aliases=['dice'],
                      description='Random roll. Provide number argument to specify range (1-100 default).')
    async def roll(self, ctx: commands.Context, *args):
        """!roll <range> or <member1, member2, ..., memberlast>"""      

        # The is_number method returns True if no arguments are given, since the for-loop is never entered.
        async def is_number(args):
            try:
                for i in range(len(args)):
                    int(args[i])
                return True
            except ValueError:
                return False
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

                random_number = random.randint(lower, upper)
                
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

    # UNFINISHED!
    @commands.command(name="removebg")
    async def remove_bg(self, ctx: commands.Context, image_url: str=None) -> None:
        if not image_url and not ctx.message.attachments:
            raise discord.DiscordException("Message has image URL or image attachment")
        
        if ctx.message.attachments:
            iamge_url = ctx.message.attachments[0].url

        img = await self.download_from_url(image_url)

        # im suer this is broken im tired cba
        async with aiohttp.ClientSession() as session:
            response = await session.post(
                image_url,
                data={'image_file': img_file,
                      'size': 'auto'},
                headers={'X-Api-Key': API_KEY}
            )
        
