import unicodedata

import discord
import requests
from discord.ext import commands

from cogs.base_cog import BaseCog
from ext.checks import owners_only


class TestingCog(BaseCog):
    """Unstable/bad/temporary commands"""

    EMOJI = ":robot:"
    
    @commands.command(name="emojis")
    async def emojis(self, ctx:commands.Context, emoji: str=None, *text: str) -> None:
        """Replace spaces with a given emoji."""
        if not emoji:
            return await ctx.send("Emoji is a required argument")
        
        if not text:
            return await ctx.send("Text is a required argument")
        
        msg = list(text)
        # Append and prepend empty strings in order for 
        # str.join() to add emoji to beginning and end of text
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
