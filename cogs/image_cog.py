import discord
from discord.ext import commands
from cogs.base_cog import BaseCog
from PIL import Image
from typing import Tuple

class ImageCog(BaseCog):
    async def _compose_image(self, ctx, template: str, resize:Tuple[int,int], offset:Tuple[int,int], user: commands.UserConverter=None) -> None:
        if not user:
            user_avatar_url = ctx.message.author.avatar_url.split("?")[0] # remove ?size=1024 
        else:
            user_avatar_url = user.avatar_url
        with open("memes/temp/temp.webp", "wb") as f:
            img = await self.download_from_url(user_avatar_url)
            f.write(img)
        # Open user's avatar
        img = Image.open("memes/temp/temp.webp", "r")
        img = img.resize(resize, resample=Image.BICUBIC)
        # Open template
        background = Image.open(f"memes/templates/{template}", "r")
        # Paste user's avatar
        background.paste(img, offset)
        # Save and post
        background.save("memes/temp/out.png")
        await ctx.send(file=discord.File("memes/temp/out.png"))
    
    @commands.command(name="fuckup", aliases=["nasa"])
    async def nasa(self, ctx: commands.Context, user: commands.UserConverter=None) -> None:
        await self._compose_image(ctx, "nasa.jpg", (100, 100), (347, 403), user)
    
    @commands.command(name="northkorea", aliases=["nk"])
    async def northkorea(self, ctx: commands.Context, user: commands.UserConverter=None) -> None:
        """TODO: Apply proper perspective transformation"""
        await self._compose_image(ctx, "northkorea1.jpg", (295, 295), (712, 195), user)
    
    @commands.command(name="cancer", aliases=["cer"])
    async def cancer(self, ctx: commands.Context, user: commands.UserConverter=None) -> None:
        await self._compose_image(ctx, "cancer.jpg", (762, 740), (772, 680), user)
