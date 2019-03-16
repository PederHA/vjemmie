from discord.ext import commands
import discord
from ext_module import ExtModule
from ext_module import PmForbidden
from random import randint
from cogs.base_cog import BaseCog

class UserCog(BaseCog):
    def __init__(self, bot: commands.Bot, log_channel_id: int=None):
        super().__init__(bot, log_channel_id)
        self.bot.remove_command('help')

    @commands.command(name="help", aliases=["Help", "hlep", "?", "pls"])
    async def send_help(self, ctx: commands.Context, cog_name: str=None, simple: str="simple"):
        """Sends information about a specific cog's commands"""
        if simple in ["n", "-", "advanced"]:
            simple = "advanced"
        if not cog_name:
            categories = "\n".join(cog.cog_name
                                   for cog in list(self.bot.cogs.values())
                                   if cog.cog_name not in self.IGNORE_HELP)
            embed = await self.get_embed(ctx, fields=[self.EmbedField("Categories", categories)])
            await ctx.send(embed=embed)
            await ctx.send("Type `!help <category> (advanced)` or `!<Category> (advanced)`")
        else:
            cog_name = cog_name.lower()
            for cog in self.bot.cogs.values():
                if cog_name == cog.cog_name.lower() and cog_name not in self.IGNORE_HELP:

                    await cog._get_cog_commands(ctx, simple)
                    break
            else:
                raise discord.DiscordException(f"No such category **{cog_name}**.")
