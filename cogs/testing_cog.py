import unicodedata

import discord
import requests
from discord.ext import commands

from cogs.base_cog import BaseCog
from ext.checks import owners_only


class TestingCog(BaseCog):
    """Unstable/bad/temporary commands"""
    
    @commands.command(name="emojis")
    async def emojis(self, ctx:commands.Context, emoji: str, *message) -> None:
        """Replace spaces with a given emoji."""
        msg = list(message)
        msg.append("")
        msg.insert(0, "")
        await ctx.send(emoji.join(msg))

    @commands.command(name="sheriff")
    async def sheriff(self, ctx: commands.Context, emoji: str) -> None:
        """Make a sheriff out of emojis."""
        out = """
        \n⁯⁯⁯⁯ 
⠀ ⠀ ⠀    🤠
　   {e}{e}{e}
    {e}   {e}　{e}
    👇  {e}{e} 👇
  　  {e}　{e}
　   {e}　 {e}
　   👢     👢
    """.format(e=emoji)
        try:
            emoji_name = unicodedata.name(emoji)
        except:
            if ":" in emoji:
                emoji_name = emoji.split(":", 3)[1]
            else:
                emoji_name = None
        if emoji_name is not None:
            out += f"\nI am the sheriff of {emoji_name.title()}"
        await ctx.send(out)

    @commands.command(name="dbg")
    @owners_only()
    async def dbg(self, ctx: commands.Context) -> None:
        breakpoint()
        print("yeah!")
