import discord
from discord.ext import commands
from ext.checks import is_pfm
from cogs.base_cog import BaseCog, EmbedField
from cogs.db_cog import DatabaseHandler
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

    @commands.command(name="gamingmoments")
    @is_pfm()
    async def get_gaming_moments(self, ctx: commands.Context) -> None:
        db = DatabaseHandler(GENERAL_DB_PATH)
        # Get names, occurences
        gaming_moments = db.get_gaming_moments()
        gaming_moments_nodiscrim = [(name.split("#")[0], occurences) for name, occurences in gaming_moments]

        # Determine formatting of embed field
        longest_name = max([len(name) for name, _ in gaming_moments_nodiscrim]) + 1 # the length of the markdown codeblock

        # Content of embed field
        fchar = self.EMBED_FILL_CHAR
        out = "\n".join([f"`{name.ljust(longest_name, fchar)}:`{fchar*3}{occurences}" for name, occurences in gaming_moments_nodiscrim])

        # Attempt to get member object for top ranking gamer
        name, discriminator = gaming_moments[0][0].split("#")
        member = None
        for memb in self.bot.get_all_members():
            if memb.name == name and memb.discriminator == discriminator:
                member = memb
                break

        # Get embed object for gamer leaderboard
        embed = await self.get_embed(ctx, fields=[EmbedField("Heated Gaming Moments", out)], color=0xe98cb0)

        # Set embed thumnail to rank 1 gamer if a matching Discord member is found
        if member:
            embed.set_thumbnail(url=member.avatar_url)
        await ctx.send(embed=embed)

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

