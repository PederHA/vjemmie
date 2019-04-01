import discord
from discord.ext import commands
from ext.checks import is_pfm
from cogs.base_cog import BaseCog, EmbedField
from utils.config import GENERAL_DB_PATH

class MemeCog(BaseCog):
    """Various meme commands"""

    # TODO: Do something like: await send_text_message(ctx, await self.read_text_file())
    @commands.command(name="goodshit")
    async def goodshit(self, ctx: commands.Context) -> None:
        await self.read_send_file(ctx, "memes/txt/goodshit.txt")

    @commands.command(name="mason")
    async def mason(self, ctx: commands.Context) -> None:
        await self.read_send_file(ctx, "memes/txt/mason.txt")

    @commands.command()
    async def psio(self, ctx: commands.Context) -> None:
        await self.read_send_file(ctx, "memes/txt/psio.txt")



    @commands.command(name="braille")
    async def braille(self, ctx: commands.Context, *text: str) -> None:
        char_map = {
            'a': '⠁',
            'b': '⠃',
            'c': '⠉',
            'd': '⠙',
            'e': '⠑',
            'f': '⠋',
            'g': '⠛',
            'h': '⠓',
            'i': '⠊',
            'j': '⠚',
            'k': '⠅',
            'l': '⠇',
            'm': '⠍',
            'n': '⠝',
            'o': '⠕',
            'p': '⠏',
            'q': '⠟',
            'r': '⠗',
            's': '⠎',
            't': '⠞',
            'u': '⠥',
            'v': '⠧',
            'x': '⠭',
            'y': '⠽',
            'z': '⠵',
            'w': '⠺',
            " ": " "
        }
        translation = str.maketrans(char_map)
        text = " ".join(text).lower()
        await ctx.send(text.translate(translation))

