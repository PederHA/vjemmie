import random
from typing import Tuple

import discord
import numpy
from discord.ext import commands

from cogs.base_cog import BaseCog


class PUBGCog(BaseCog):
    """PUBG commands"""
    
    EMOJI = "<:pubghelm:565522877902749726>"

    @commands.command(
        name="drop", aliases=["roulette", "plane"], description="u fucking wot"
    )
    async def drop(self, ctx: commands.Context, map_:str=None, hot: str=None):
        """
        Chooses random drop location on a given map.
        """
        MAPS = {
            "miramar": { 
                "locations": 
                    [
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
                    ],
                "hot_idx": 6
            },
            "erangel": {
                "locations": 
                    [
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
                    ],
                "hot_idx": 9
                }
        }

        # Get PUBG map
        pubgmap = MAPS.get(map_.lower())

        # Raise exception if map cannot be found
        if not pubgmap:
            return await ctx.send("Invalid map!")

        # Get list of locations for selected map
        locations = pubgmap.get("locations")
        
        # Determine drop location selection logic
        if hot:
            hot_idx = pubgmap.get("hot_idx")
            location = random.choice(locations[:hot_idx])
        else:
            location = random.choice(locations)

        await ctx.send(location)

    # Start of Crate command
    @commands.command(
        name="crate",
        aliases=["crateplay", "dibs", "airdrop"],
        description="nah mate ur not getting the awm",
    )
    async def crate(self, ctx: commands.Context, *players):
        """
        Distributes airdrop loot among a squad.
        """

        default_squad = ("Simon", "Hugo", "Travis", "Steve")

        # Resort to default squad if no players arguments
        if not players:
            squad = default_squad

        # Get players from ctx.author's voice channel
        elif len(players) == 1 and players[0] in ["channel", "c", "ch", "chanel"]:
            try:
                squad = [user for user in await self.get_users_in_voice(ctx)]
            except AttributeError:
                return await ctx.send(
                    f"Must be connected to a voice channel to use `{players[0]}` argument."
                )
            else:
                if len(squad) < 2:
                    return await ctx.send(
                        "A minimum number of 2 people is required!"
                        )                    
      
       # At least 2 players must be specified 
        elif len(players) == 1:
            return await ctx.send("Can't roll crate for 1 player.")
        
        else:
            squad = args

        # Limit names to one word
        squad = [name.split(" ")[0] for name in squad]

        # Determines size of squad and distributes guns accordingly.
        # Returns size of squad and gun list containing n=squadsize lists.
        gunsplit, armorsplit = await self.roll_guns(squad)

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
