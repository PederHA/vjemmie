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

    @commands.command(name="help")
    async def send_help(self, ctx: commands.Context, cog_name: str=None):
        """Sends information about a specific cog's commands"""
        if not cog_name:
            categories = "\n".join([cog[:-3] for cog in list(self.bot.cogs.keys())])
            embed = await self.get_embed(ctx, fields=[self.EmbedField("Categories", categories)])
            await ctx.send(embed=embed)
            await ctx.send("Type `!help <category>`")
        else:
            cog_name = cog_name.lower()
            for cog in self.bot.cogs.values():
                if cog.cog_name.lower() == cog_name:
                    await cog._get_cog_commands(ctx)
