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
    async def send_help(self, ctx: commands.Context, cog_name: str=None, simple: str="simple"):
        """Sends information about a specific cog's commands"""
        
        # Enable advanced !help output
        if simple in ["n", "-", "advanced"]:
            simple = "advanced"
        
        # Send message listing all possible !help categories
        if not cog_name:
            categories = "\n".join(cog.cog_name
                                   for cog in list(self.bot.cogs.values())
                                   if cog.cog_name not in self.DISABLE_HELP)
            await self.send_embed_message(ctx, "Categories", categories)
            await ctx.send("Type `!help <category> (advanced)` for a specific category.\n"
                           "Or type `!commands` to show all available commands.")
        
        # Send help message for specific category
        else:
            cog_name = cog_name.lower()
            for cog in self.bot.cogs.values():
                if cog_name == cog.cog_name.lower() and cog_name not in self.DISABLE_HELP:

                    await cog._get_cog_commands(ctx, simple)
                    break
            else:
                raise discord.DiscordException(f"No such ategory **{cog_name}**.")
    
    @commands.command(name="commands")
    async def show_commands(self, ctx:commands.Context) -> None:
        l = []
        for cog in self.bot.cogs.values():
            if cog.cog_name in self.DISABLE_HELP:
                continue
            cmds = await cog._get_cog_commands(ctx, "simple", rtn=True)
            l.append(f"{cog.cog_name}\n{cmds}")
        out = "\n".join(l)   
        await self.send_embed_message(ctx, "Commands", out, color="red")
    
    
    @commands.command(name="invite", aliases=["get_invite"])
    async def invitelink(self, ctx: commands.Context, priv_level: int=None) -> None:
        """Get discord bot invite URL"""
        base_url = "https://discordapp.com/api/oauth2/authorize?client_id={id}&scope=bot&permissions={permissions}"
        
        # Privilege levels {Lvl: (Name, Permission integer)}
        # Dict[int, Tuple[str, int]]
        levels = {
            1: ("Minimal", 70642752),
            2: ("Standard (Recommended)", 133557312),
            3: ("Admin", 2146958839) 
        }
        
        # Post help text if no priv level argument
        if not priv_level:
            lvls = "\n".join([f"**{k}**: {v[0]}" for k, v in levels.items()])
            out_msg = f"Specify a privilege level:\n{lvls}"
            await self.send_embed_message(ctx, f"!{ctx.invoked_with}", out_msg)
            return await ctx.send(f"Type `!{ctx.invoked_with} <privilege level>`")
        
        lvl = levels.get(priv_level)
        if not lvl:
            return await ctx.send(f"{priv_level} is not a valid privilege level!")

        permissions = lvl[1] # Permission integer
        
        url = base_url.format(id=self.bot.user.id, permissions=permissions)
        await ctx.send(url)
        