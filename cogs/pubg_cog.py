import random
from typing import Tuple

import discord
import numpy
from discord.ext import commands

from bot_resources import GUILDS, NON_PUBG_PLAYERS
from cogs.base_cog import BaseCog
from cogs.db_cog import DatabaseHandler
from events_module import contains_rad

from utils.config import GENERAL_DB_PATH


class PUBGCog(BaseCog):
    """PUBG Bot Commands
    """
    
    #@commands.command(
    #    name="drop", aliases=["roulette", "plane"], description="u fucking wot"
    #)
    #async def drop(self, ctx: commands.Context, map_:str=None, opt: str=None):
    #    """
    #    ``!drop``command that chooses random drop location on a given PUBG map.
    #    ----
    #    
    #    Args: tuple containing user arguments provided after typing !drop.
    #    """
#
    #    MIRAMAR_LOCATIONS_ALL = [
    #        "El Pozo",
    #        "Pecado",
    #        "San Martín",
    #        "Hacienda del Patrón",
    #        "Campo Militar",
    #        "Los Leones",
    #        "Monte Nuevo",
    #        "El Azahar",
    #        "Cruz del Valle",
    #        "Tierra Bronca",
    #        "Torre Ahumada",
    #        "Impala",
    #        "La Cobrería",
    #    ]
#
    #    MIRAMAR_LOCATIONS_HOT = MIRAMAR_LOCATIONS_ALL[:6]
#
    #    ERANGEL_LOCATIONS_ALL = [
    #        "South George",
    #        "North George",
    #        "Yasnaya",
    #        "School",
    #        "Pochinki",
    #        "Mylta",
    #        "Mylta Power",
    #        "Military Base",
    #        "Novorepnoye",
    #        "Lipovka",
    #        "Prison",
    #        "Shelter",
    #        "Primorsk",
    #        "Gatka",
    #        "Zharki",
    #    ]
#
    #    ERANGEL_LOCATIONS_HOT = ERANGEL_LOCATIONS_ALL[:9]
#
    #    VALID_MAPS = ["erangel", "miramar", "sanhok [NYI!]"]
    #    HOT = ["hot"]
    #    invalid_args_msg = 'Invalid arguments. Syntax: "!drop <map> (hot)"'
    #    invalid_map = False
    #    no_map = False
    #    pubgmap = map_.lower()
    #    
    #    if pubgmap not in VALID_MAPS:
    #        await ctx.send("Invalid")
    #        raise Exception
#
    #    # Only valid_args if an argument is given.
    #    if map_ is not None:
#
    #        
    #        if opt.lower() == "hot":
    #            hot = True
    #        else:
    #            hot = False
#
    #        # Check if arg is a valid pubg map
    #        if pubgmap in VALID_MAPS:
    #            if pubgmap == VALID_MAPS[1]
    #                if hot:
    #                    droplocation = random.choice(MIRAMAR_LOCATIONS_HOT)
    #                else:
    #                    droplocation = random.choice(MIRAMAR_LOCATIONS_ALL)
    #            elif pubgmap == VALID_MAPS[0]
    #                if hot:
    #                    droplocation = random.choice(ERANGEL_LOCATIONS_HOT)
    #                else:
    #                    droplocation = random.choice(ERANGEL_LOCATIONS_ALL)
#
    #            await ctx.send("Drop location: " + droplocation)
#
    #        else:
    #            invalid_map = True
#
    #    else:
    #        no_map = True
    #    
    #    if no_map or invalid_map:
    #        if no_map:
    #            message = "No map specified. Type "
    #        if invalid_map:
    #            message = "Invalid map specified. Type "
    #        
    #        n = 0
    #        for pubgmap in VALID_MAPS:
    #            n += 1
    #            message+= f"`!drop {pubgmap} (hot)`"
    #            if n < len(VALID_MAPS):
    #                message += " or "
    #        else:
    #            message += "."
    #        await ctx.send(message)


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

        bot_msg = ""
        default_squad = ("Simon", "Hugo", "Travis", "Steve")

        if args == ():
            squad = default_squad
        elif args[0].isdigit():
            n_players = int(args[0])
            if 1 < n_players <= 4:
                int_list = list(range(1, n_players))
                squad_list = [str(n) for n in int_list]
                squad = squad_list
            elif n_players > 4:
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
        
        if bot_msg:
            await ctx.send(bot_msg)
            raise Exception(f"Exception in !crate: {bot_msg}")

        # Limit names to one word
        squad = [name.split(" ")[0] for name in squad]

        if contains_rad(squad):
            await ctx.message.add_reaction(":8xscope:417396529452810241")

        # Determines size of squad and distributes guns accordingly.
        # Returns size of squad and gun list containing n=squadsize lists.
        gunsplit, armorsplit = await self.roll_guns(squad)
        #db = DatabaseHandler(GENERAL_DB_PATH)
        #for idx, player in enumerate(squad):
        #    db.crate_rolls(player, [gun for gun in gunsplit[idx]], [armor for armor in armorsplit[idx]])
        output = await self.generate_crate_text(squad, gunsplit, armorsplit)

        await ctx.send(output)

    async def roll_guns(self, squad: list) -> Tuple[list, list]:
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
        EQUIPMENT = list(set(_CRATEGUNS_ALL) - set(GUNS))

        # Shuffle lists
        random.shuffle(squad)
        random.shuffle(GUNS)
        random.shuffle(EQUIPMENT)

        # Divide lists by len(squad)
        squadsize = len(squad)

        gunsplit = numpy.array_split(GUNS, squadsize)
        armorsplit = numpy.array_split(EQUIPMENT, squadsize)

        # Reroll if one person gets 4 items in a 3-man squad.
        if squadsize == 3:
            while any([True if len(list(guns)+list(armor))>=4 else False for guns, armor in zip(gunsplit, armorsplit)]):
                random.shuffle(gunsplit)
                random.shuffle(armorsplit)

        return gunsplit, armorsplit

    async def generate_crate_text(self, squad: list, gunsplit: list, armorsplit: list) -> str:
        """
        Creates output message for !crate command.
        """              
        if squad[0].isdigit(): 
            # Sort squad numerically
            squad.sort() 
        msg = "```"
        _spc = len(max(squad, key=len)) + 1
        for idx, player in enumerate(squad):
            if player.islower():
                player = player.capitalize()
            name_spc = " "*(_spc-len(player))
            gun = " ".join(gunsplit[idx])
            equipment = " ".join(armorsplit[idx])
            msg += f"{player}:{name_spc} {gun} {equipment}\n"
        msg += "```"
        return msg

    async def get_squad_from_channel(self, ctx) -> list:
        """
        Get members from voice channel. Ignores users in blacklist.
        """
        squad_list = []
        try:
            for member in ctx.message.author.voice.channel.members:
                if not member.voice.self_deaf:
                    if member.id not in NON_PUBG_PLAYERS:
                        squad_list.append(member.name)
        except AttributeError:
            pass # This error will be handled by `crate` method. 
        return squad_list
