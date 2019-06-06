import sys
from contextlib import suppress
from random import randint

import discord
import psutil
from discord.ext import commands

from cogs.base_cog import BaseCog, EmbedField
from config import AUTHOR_MENTION, NO_ARGS
from utils.exceptions import CategoryError, CogError, CommandError


class UserCog(BaseCog):
    """Help commands."""

    def __init__(self, bot: commands.Bot):
        super().__init__(bot)
        self.bot.remove_command('help')

    @commands.command(name="help", aliases=["Help", "hlep", "?", "pls"])
    async def send_help(self, ctx: commands.Context, cog_name: str=None, simple: str="y"):
        """Sends information about a specific cog's commands"""
        
        # Enable advanced !help output
        if simple in NO_ARGS + ["advanced"]:
            simple = False
        
        # Only include cogs that have commands that pass checks for current ctx
        cogs = []
        for cog in await self.get_cogs():
            try:
                await cog._get_cog_commands(ctx, rtn=True)
            except CommandError: # Cog has no commands that pass checks
                pass
            else:
                cogs.append(cog)
        
        # Raise exception if no cog commands are available
        if not cogs:
            raise CogError(
                "Bot has no cogs, or cog commands are unavailable for the current server or channel."
                )
        
        # Send help message for specific category
        if cog_name:
            cog_name = cog_name.lower()
            for cog in cogs:
                if cog_name == cog.cog_name.lower():
                    return await cog._get_cog_commands(ctx, simple)
            else:
                raise CategoryError(f"No such category **{cog_name}**.")
          
        # Send message listing all possible !help categories if no category
        # Make an embed field for each cog
        fields = [EmbedField(f"{cog.EMOJI} {cog.cog_name}", cog.__doc__+"\n\xa0") for cog in cogs if cog.__doc__]
        embed = await self.get_embed(ctx, title="CATEGORIES", fields=fields, inline=False)
        
        # Send embeds
        await ctx.send(embed=embed)
        
        # Send !help usage instructions
        await ctx.send("Type `!help <category> (advanced)` for a specific category.\n"
                        "Or type `!commands` to show all available commands.")

    @commands.command(name="commands")
    async def show_commands(self, ctx:commands.Context, verbosity: str="simple") -> None:
        """Display all bot commands."""
        l = []
        simple = verbosity not in ["advanced", "y", "args"]
        for cog in await self.get_cogs():
            # Ignore cogs returning no commands due to failed checks or lack of commands
            with suppress(CommandError):
                cmds = await cog._get_cog_commands(ctx, simple, rtn=True)
                l.append(f"{cog.EMOJI} **{cog.cog_name}**\n_{cog.__doc__}_\n{cmds}")
        
        if not l:
            raise CommandError("No commands are available!")
        
        out = "\n".join(l)
           
        await self.send_embed_message(ctx, "Commands", out, color="red")
    
    
    @commands.command(name="invite", aliases=["get_invite"])
    async def invitelink(self, ctx: commands.Context) -> None:
        """Get discord bot invite URL"""
        base_url = "https://discordapp.com/api/oauth2/authorize?client_id={id}&scope=bot&permissions={permissions}"
        
        levels = {
            "Minimal": 70642752,
            "Standard (Recommended)": 133557312,
            "Admin": 2146958839 
        }
        
        out_str = "\n".join(
            [
            f"[**{level}**]({base_url.format(id=self.bot.user.id, permissions=permissions)})"
            for level, permissions in levels.items()
            ]
        )
        
        embed = await self.get_embed(ctx,
                                     author=f"Invite {self.bot.user.name}",
                                     author_icon="https://discordapp.com/assets/2c21aeda16de354ba5334551a883b481.png",
                                     description=out_str,
                                     color="blurple"
                                     )
        return await ctx.send(embed=embed)


    @commands.command(name="about", aliases=["info"])
    async def about(self, ctx: commands.Context) -> None:
        """General bot information."""
        # Memory
        mem = psutil.virtual_memory()
        mem_total_mb = round(mem.total / 1000000)
        mem_used_mb = round(mem.used / 1000000)
        #mem_graphic = f"[{'l'*round(mem.percent/10)}{'_'*round((100-mem.percent)/10)}]"

        # Soundboard
        sound_cog = self.bot.get_cog("SoundCog")
        try:
            n_soundfiles = len(sound_cog.sound_list)
        except:
            n_soundfiles = 0
        
        fields = [
            EmbedField(name="Owner", value=AUTHOR_MENTION),
            EmbedField(name="Running on", value=f"<:python:570331647933677590> Python {sys.version.split(' ')[0]}"), 
            EmbedField(name="Command categories", value=len(await self.get_cogs())),
            EmbedField(name="Useful commands", value="`!help`, `!commands`, `!changelog`"),
            EmbedField(name="Soundboard files", value=f"{n_soundfiles}"),
            EmbedField(name="Memory usage", value=f"{mem_used_mb} / {mem_total_mb} MB"),
            EmbedField(name="CPU Usage", value=f"{psutil.cpu_percent()}%"),
            EmbedField(name="Uptime", value=await ctx.invoke(self.bot.get_command("uptime"), rtn=True)),   
        ]
        
        embed = await self.get_embed(ctx,
                                     author=self.bot.user.name,
                                     author_icon=self.bot.user.avatar_url._url,
                                     description="Top secret bot running on the Tiger Mafia mainframe.",
                                     fields=fields)
            
        await ctx.send(embed=embed)   
