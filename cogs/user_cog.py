from contextlib import suppress
from random import randint

import discord
from discord.ext import commands

from cogs.base_cog import BaseCog


class UserCog(BaseCog):
    """Help commands."""

    def __init__(self, bot: commands.Bot):
        super().__init__(bot)
        self.bot.remove_command('help')

    @commands.command(name="help", aliases=["Help", "hlep", "?", "pls"])
    async def send_help(self, ctx: commands.Context, cog_name: str=None, simple: str="y"):
        """Sends information about a specific cog's commands"""
        
        # Enable advanced !help output
        if simple in ["n", "-", "advanced"]:
            simple = False
        
        cogs = await self.get_cogs()

        # Send help message for specific category
        if cog_name:
            cog_name = cog_name.lower()
            for cog in cogs:
                if cog_name == cog.cog_name.lower():
                    return await cog._get_cog_commands(ctx, simple)
            else:
                raise discord.DiscordException(f"No such category **{cog_name}**.")
          
        # Send message listing all possible !help categories if no category
        # Make an embed field for each cog
        fields = [self.EmbedField(f"{cog.EMOJI} {cog.cog_name}", cog.__doc__+"\n\xa0") for cog in cogs if cog.__doc__]
        embed = await self.get_embed(ctx, title="CATEGORIES", fields=fields, inline=False)
        
        # Send embeds
        await ctx.send(embed=embed)
        
        # Send !help usage instructions
        await ctx.send("Type `!help <category> (advanced)` for a specific category.\n"
                        "Or type `!commands` to show all available commands.")

    @commands.command(name="commands")
    async def show_commands(self, ctx:commands.Context) -> None:
        l = []
        for cog in await self.get_cogs():
            # Ignore cogs returning no commands due to failed checks or lack of commands
            with suppress(AttributeError):
                cmds = await cog._get_cog_commands(ctx, "simple", rtn=True)
                l.append(f"{cog.EMOJI} **{cog.cog_name}**\n_{cog.__doc__}_\n{cmds}")
        out = "\n".join(l)   
        await self.send_embed_message(ctx, "Commands", out, color="red")
    
    
    @commands.command(name="invite", aliases=["get_invite"])
    async def invitelink(self, ctx: commands.Context, priv_level: int=None) -> None:
        """Get discord bot invite URL"""
        base_url = "https://discordapp.com/api/oauth2/authorize?client_id={id}&scope=bot&permissions={permissions}"
        
        levels = {
            "Minimal": 70642752,
            "Standard (Recommended)": 133557312,
            "Admin": 2146958839 
        }
        
        out_str = "\n".join(
            [
            f"[{level}]({base_url.format(id=self.bot.user.id, permissions=permissions)})"
            for level, permissions in levels.items()
            ]
        )
        
        return await self.send_embed_message(ctx, "Invite links", out_str)
