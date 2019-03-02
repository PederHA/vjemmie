import discord
from discord.ext import commands
from cogs.base_cog import BaseCog
from PIL import Image, ImageDraw, ImageFont
from typing import Tuple, Union, List
from itertools import zip_longest

class ImageCog(BaseCog):
    """Various commands for creating dank memes featuring a user's avatar.
    """
    async def _composite_images(self, 
                             ctx: commands.Context, 
                             template: str, 
                             resize:Union[Tuple[int,int], list], 
                             offset:Union[Tuple[int,int], list], 
                             user: commands.UserConverter=None,
                             text: Union[List[dict], dict]=None, 
                             template_overlay: bool=False) -> None:
        """Creates a composite image of a user's avatar and a given template.

        Args:
            ctx (commands.Context): Discord Context
            template (str): File name of image to use as template
            resize (Union[Tuple[int,int], list]): tuple (width, height) or list of tuples (w, h)
            offset (Union[Tuple[int,int], list]): tuple (off_x, off_y) or list of tuples (off_x, off_y)
            user (commands.UserConverter, optional): Discord User
            text (dict, optional): Text overlay options. (check ImageCog._add_text for info) 
            template_overlay (bool, optional): Puts overlay on top of user's avatar.
        """

        if not user:
            user_avatar_url = ctx.message.author.avatar_url.split("?")[0] # remove ?size=1024 
        else:
            user_avatar_url = user.avatar_url
        
        # Download user's avatar
        with open("memes/temp/temp.webp", "wb") as f:
            avatar_img = await self.download_from_url(user_avatar_url)
            f.write(avatar_img)
        
        # Open user's avatar
        img = Image.open("memes/temp/temp.webp", "r")
        
        # Open template
        background = Image.open(f"memes/templates/{template}", "r")
        # Convert template to RGBA
        if background.mode == "RGB": 
            background.putalpha(255)
        
        # Add avatar to template
        if template_overlay:
            # Template is composited over user's avatar
            new = Image.new("RGBA", background.size)
            new.paste(img, offset)
            background = Image.alpha_composite(new, background)
        else:
            # Paste user's avatar
            if isinstance(offset, tuple): # Ensures backwards compatibility
                img = img.resize(resize, resample=Image.BICUBIC)
                background.paste(img, offset)
            elif isinstance(offset, list):
                if not isinstance(resize, list):
                    # Create list of tuples of size n=len(offset) if resize is not type(list)
                    resize = [resize]*len(offset)
                # Fill with first value of shortest list if number of elements are not identical
                fill_value = max(resize, offset)[0] if len(resize) != len(offset) else None
                # Paste user avatars
                for off, rsz in zip_longest(offset, resize, fillvalue=fill_value):
                    img = img.resize(rsz, resample=Image.BICUBIC)
                    background.paste(img, off)
        
        if text:
            if isinstance(text, dict):
                background = await self._add_text(ctx, background, text)
            elif isinstance(text, list):
                for txt in text:
                    background = await self._add_text(ctx, background, txt)
       
        # Save and post
        background.save("memes/temp/out.png")
        await ctx.send(file=discord.File("memes/temp/out.png"))
    
    async def _add_text(self, ctx, background: Image.Image, text: dict) -> Image.Image:
        """Adds text to background"""
        # Get text options
        font_name = text.get("font", "LiberationSans-Regular.ttf") # Default Helvetica Neue copy
        font_size = text.get("size", 20)
        text_offset = text.get("offset", (0, 0)) 
        text_color = text.get("color", (255, 255, 255, 255)) # Default white
        text_content = text.get("content", ctx.message.author.name)
        
        # Get new image
        _txt = Image.new("RGBA", background.size)
        # Get font
        font = ImageFont.truetype(f"memes/fonts/{font_name}", font_size)
        # Get a drawing context
        d = ImageDraw.Draw(_txt)
        d.text(text_offset, text_content, font=font, fill=text_color)
        
        # Return alpha composite of background and text
        return Image.alpha_composite(background, _txt)

    @commands.command(name="fuckup", aliases=["nasa"])
    async def nasa(self, ctx: commands.Context, user: commands.UserConverter=None) -> None:
        """https://i.imgur.com/HcjIbpP.jpg"""
        await self._composite_images(ctx, "nasa.jpg", (100, 100), (347, 403), user)
    
    @commands.command(name="northkorea", aliases=["nk"])
    async def northkorea(self, ctx: commands.Context, user: commands.UserConverter=None) -> None:
        """https://i.imgur.com/PiqzXNs.jpg"""
        await self._composite_images(ctx, "northkorea1.jpg", (295, 295), (712, 195), user)
    
    @commands.command(name="cancer", aliases=["cer"])
    async def cancer(self, ctx: commands.Context, user: commands.UserConverter=None) -> None:
        """https://i.imgur.com/vDtktIq.jpg"""
        await self._composite_images(ctx, "cancer.jpg", (762, 740), (772, 680), user)

    @commands.command(name="mlady", aliases=["neckbeard"])
    async def mlady(self, ctx: commands.Context, user: commands.UserConverter=None) -> None:
        """https://i.imgur.com/2LQkErQ.png"""
        await self._composite_images(ctx, "mlady.png", (200, 200), (161, 101), user, template_overlay=True)

    @commands.command(name="loud", aliases=["loudest"])
    async def loud(self, ctx: commands.Context, user: commands.UserConverter=None) -> None:
        """https://i.imgur.com/y7y7MRt.jpg"""
        await self._composite_images(ctx, "loud.jpg", (190, 190), (556, 445), user)
    
    @commands.command(name="guys", aliases=["guys_only_want_one_thing", "guyswant", "onething"])
    async def guys_only_want_one_thing(self, ctx: commands.Context, user: commands.UserConverter=None) -> None:
        """https://i.imgur.com/5oUe8VN.jpg"""
        await self._composite_images(ctx, "guyswant.jpg", (400, 400), (121, 347), user)
    
    @commands.command(name="furry")
    async def furry(self, ctx: commands.Context, user: commands.UserConverter=None) -> None:
        """https://i.imgur.com/Jq3uu02.png"""
        await self._composite_images(ctx, "furry.png", (230, 230), (26, 199), user, template_overlay=True)

    @commands.command(name="autism", aliases=["thirtyseven"])
    async def autism(self, ctx: commands.Context, user: commands.UserConverter=None) -> None:
        """https://i.imgur.com/HcjIbpP.jpg"""
        await self._composite_images(ctx, "autism.jpg", (303, 255), (0, 512), user)
   
    @commands.command(name="disabled")
    async def disabled(self, ctx: commands.Context, user: commands.UserConverter=None) -> None:
        """https://i.imgur.com/hZSghxu.jpg"""
        await self._composite_images(ctx, "disabled.jpg", (320, 320), (736, 794), user)

    @commands.command(name="autism2")
    async def autism2(self, ctx: commands.Context, user: commands.UserConverter=None) -> None:
        """https://i.imgur.com/6lxlqPk.jpg"""
        text_content = user.name if user else ctx.message.author.name
        text = {
            "content": text_content,
            "size": 20,
            "offset": (96, 0),
            "font": "LiberationSans-Regular.ttf",
            "color": (0, 0, 0, 255)
            }
        text2 = dict(text)
        text2["offset"] = (96, 551)
        _txt = [text, text2]
        await self._composite_images(ctx, "autism2.jpg", [(73, 73), (73, 73)], [(15, 1), (15, 551), (123, 709)], user, text=_txt)
    
    @commands.command(name="fatfuck")
    async def fatfuck(self, ctx: commands.Context, user: commands.UserConverter=None) -> None:
        """https://i.imgur.com/Vbkfu4u.jpg"""
        await self._composite_images(ctx, "fatfuck.jpg", (385, 385), (67, 0), user)