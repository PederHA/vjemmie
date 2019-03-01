import discord
from discord.ext import commands
from cogs.base_cog import BaseCog
from PIL import Image
from typing import Tuple

class ImageCog(BaseCog):
    async def _composit_image(self, 
                             ctx, 
                             template: str, 
                             resize:Tuple[int,int], 
                             offset:Tuple[int,int], 
                             user: commands.UserConverter=None, 
                             template_overlay: bool=False) -> None:
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
        # Add avatar to template
        if template_overlay:
            # Template is composited over user's avatar
            new = Image.new("RGBA", background.size)
            new.paste(img, offset)
            background = Image.alpha_composite(new, background)
        else:
            # Paste user's avatar
            background.paste(img, offset)
        # Save and post
        background.save("memes/temp/out.png")
        await ctx.send(file=discord.File("memes/temp/out.png"))
    
    @commands.command(name="fuckup", aliases=["nasa"])
    async def nasa(self, ctx: commands.Context, user: commands.UserConverter=None) -> None:
        await self._composit_image(ctx, "nasa.jpg", (100, 100), (347, 403), user)
    
    @commands.command(name="northkorea", aliases=["nk"])
    async def northkorea(self, ctx: commands.Context, user: commands.UserConverter=None) -> None:
        """TODO: Apply proper perspective transformation"""
        await self._composit_image(ctx, "northkorea1.jpg", (295, 295), (712, 195), user)
    
    @commands.command(name="cancer", aliases=["cer"])
    async def cancer(self, ctx: commands.Context, user: commands.UserConverter=None) -> None:
        await self._composit_image(ctx, "cancer.jpg", (762, 740), (772, 680), user)

    @commands.command(name="mlady", aliases=["neckbeard"])
    async def mlady(self, ctx: commands.Context, user: commands.UserConverter=None) -> None:
        await self._composit_image(ctx, "mlady.png", (200, 200), (161, 101), user, template_overlay=True)

    @commands.command(name="loud", aliases=["loudest"])
    async def loud(self, ctx: commands.Context, user: commands.UserConverter=None) -> None:
        await self._composit_image(ctx, "loud.jpg", (190, 190), (556, 445), user)
    
    @commands.command(name="guys", aliases=["guys_only_want_one_thing", "guyswant", "onething"])
    async def guys_only_want_one_thing(self, ctx: commands.Context, user: commands.UserConverter=None) -> None:
        await self._composit_image(ctx, "guyswant.jpg", (400, 400), (121, 347), user)

