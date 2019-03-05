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
                             user: commands.MemberConverter=None,
                             text: Union[List[dict], dict]=None,
                             template_overlay: bool=False) -> None:
        """Creates a composite image of a user's avatar and a given template.
        
        Parameters
        ----------
        ctx : `commands.Context`
            Discord Context object
        template : `str`
            File name of image to be used as template. 
            Must be located in memes/templates/
        resize : `Union[Tuple[int,int], list]`
            tuple (width, height) or list of tuples (w, h). A list 
            indicates that multiple instances of a user's avatar is 
            to be added to the template image.
        offset : `Union[Tuple[int,int], list]`
            tuple (off_x, off_y) or list of tuples (off_x, off_y).
            Same logic as `resize` with regards to lists.
        user : `commands.MemberConverter`, optional
            A Discord user. If specified, this user's avatar is 
            downloaded in place of the message author's.
        text : `Union[List[dict], dict]`, optional
            Dict should contain arguments corresponding to 
            `ImageCog._add_text()` parameters. Passing in a list 
            indicates multiple text overlays.
        template_overlay : `bool`, optional
            If True, the order of template and avatar is reversed, 
            and the template is placed over the avatar.
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
        user_avatar = Image.open("memes/temp/temp.webp", "r")

        # Open template
        background = Image.open(f"memes/templates/{template}", "r")

        # Convert template to RGBA
        if background.mode == "RGB":
            background.putalpha(255) # puts an alpha channel on the image

        # Add avatar to template
        background = self._do_paste(background, user_avatar, resize, offset, template_overlay)
        

        # Add text
        if text:
            if isinstance(text, dict):
                background = await self._add_text(ctx, background, **text)
            elif isinstance(text, list):
                for txt in text:
                    background = await self._add_text(ctx, background, **txt)

        # Save and post
        background.save("memes/temp/out.png")
        await ctx.send(file=discord.File("memes/temp/out.png"))
    
    def _resize_paste(self, 
                      background: Image.Image, 
                      overlay: Image.Image, 
                      resize: Tuple[int, int], 
                      offset: Tuple[int, int]) -> Image.Image:
        """Resizes an image `overlay` and pastes it to `background`
        
        Parameters
        ----------
        background : `Image.Image`
            Image that will have overlay pasted to it
        overlay : `Image.Image`
            Image to paste on to background
        resize : `Tuple[int, int]`
            Pasted image size in pixels (w, h)
        offset : `Tuple[int, int]`
            Pasted image offset in pixels (x, y)
        
        Returns
        -------
        `Image.Image`
            Image background with Image overlay pasted on top of it
        """
        overlay = overlay.resize(resize, resample=Image.BICUBIC)
        background.paste(overlay, offset)
        return background 
    
    def _do_paste(self, 
                  background: Image.Image, 
                  user_avatar: Image.Image, 
                  resize: Union[tuple, list], 
                  offset: Union[tuple, list],
                  template_overlay: bool) -> Image.Image:
        if isinstance(offset, tuple):
            if not template_overlay:
                background = self._resize_paste(background, user_avatar, resize, offset)
            else:
                new = Image.new("RGBA", background.size)
                new = self._resize_paste(new, user_avatar, resize, offset)
                background = Image.alpha_composite(new, background)                    
        elif isinstance(offset, list):
            if not isinstance(resize, list):
                # Create list of tuples of size n=len(offset) if resize is not type(list)
                resize = [resize]*len(offset)
            # Fill with first value of shortest list if number of elements are not identical
            fill_value = max(resize, offset)[0] if len(resize) != len(offset) else None
            # Paste user avatars
            for off, rsz in zip_longest(offset, resize, fillvalue=fill_value):
                if not template_overlay:
                    background = self._resize_paste(background, user_avatar, rsz, off)
                else:
                    new = Image.new("RGBA", background.size)
                    new = self._resize_paste(new, user_avatar, rsz, off)
                    background = Image.alpha_composite(new, background)
        return background   

    async def _add_text(self,
                        ctx: commands.Context,
                        background: Image.Image,
                        font: str = None,
                        size: int = 20,
                        offset: Tuple[int, int] = (0, 0),
                        color: Tuple[int, int, int, int] = (255, 255, 255, 255),
                        content: str = None) -> Image.Image:
        """Adds text to an image by creating an alpha composite of a given
        image and one or more generated lines of text.
        
        Parameters
        ----------
        ctx : `commands.Context`
            Discord context object for retrieving message author name
        background : `Image.Image`
            Image to be modified
        font : `str`, optional
            Name of font file to use. Must be located in memes/fonts/.
        size : `int`, optional
            Font size in points
        offset : `Tuple[int, int]`, optional
            Offset of the text string placement in pixels. (0, 0) corresponds to top left in the image.
        color : `Tuple[int, int, int, int]`, optional
            The color of the text supplied in the format (red, green, blue, alpha)
        content : `str`, optional
            Text to be added to image. If None, ctx.message.author name is used in
            place of a user-provided string.
        
        Returns
        -------
        `Image.Image`
            A composite of image `background` and generated text
        """

        if not font:
            font = "LiberationSans-Regular.ttf"
        if not content:
            content = ctx.message.author

        # Get new image
        _txt = Image.new("RGBA", background.size)
        # Get font
        font = ImageFont.truetype(f"memes/fonts/{font}", size)
        # Get a drawing context
        d = ImageDraw.Draw(_txt)
        d.text(offset, content, font=font, fill=color)

        # Return alpha composite of background and text
        return Image.alpha_composite(background, _txt)

    @commands.command(name="fuckup", aliases=["nasa"])
    async def nasa(self, ctx: commands.Context, user: commands.MemberConverter=None) -> None:
        """https://i.imgur.com/HcjIbpP.jpg"""
        await self._composite_images(ctx, "nasa.jpg", (100, 100), (347, 403), user)

    @commands.command(name="northkorea", aliases=["nk"])
    async def northkorea(self, ctx: commands.Context, user: commands.MemberConverter=None) -> None:
        """https://i.imgur.com/PiqzXNs.jpg"""
        await self._composite_images(ctx, "northkorea1.jpg", (295, 295), (712, 195), user)

    @commands.command(name="cancer", aliases=["cer"])
    async def cancer(self, ctx: commands.Context, user: commands.MemberConverter=None) -> None:
        """https://i.imgur.com/vDtktIq.jpg"""
        await self._composite_images(ctx, "cancer.jpg", (762, 740), (772, 680), user)

    @commands.command(name="mlady", aliases=["neckbeard"])
    async def mlady(self, ctx: commands.Context, user: commands.MemberConverter=None) -> None:
        """https://i.imgur.com/2LQkErQ.png"""
        await self._composite_images(ctx, "mlady.png", (200, 200), (161, 101), user, template_overlay=True)

    @commands.command(name="loud", aliases=["loudest"])
    async def loud(self, ctx: commands.Context, user: commands.MemberConverter=None) -> None:
        """https://i.imgur.com/y7y7MRt.jpg"""
        await self._composite_images(ctx, "loud.jpg", (190, 190), (556, 445), user)

    @commands.command(name="guys", aliases=["guyswant"])
    async def guys_only_want_one_thing(self, ctx: commands.Context, user: commands.MemberConverter=None) -> None:
        """https://i.imgur.com/5oUe8VN.jpg"""
        await self._composite_images(ctx, "guyswant.jpg", (400, 400), (121, 347), user)

    @commands.command(name="furry")
    async def furry(self, ctx: commands.Context, user: commands.MemberConverter=None) -> None:
        """https://i.imgur.com/Jq3uu02.png"""
        await self._composite_images(ctx, "furry.png", (230, 230), (26, 199), user, template_overlay=True)

    @commands.command(name="autism", aliases=["thirtyseven"])
    async def autism(self, ctx: commands.Context, user: commands.MemberConverter=None) -> None:
        """https://i.imgur.com/HcjIbpP.jpg"""
        await self._composite_images(ctx, "autism.jpg", (303, 255), (0, 512), user)

    @commands.command(name="disabled")
    async def disabled(self, ctx: commands.Context, user: commands.MemberConverter=None) -> None:
        """https://i.imgur.com/hZSghxu.jpg"""
        await self._composite_images(ctx, "disabled.jpg", (320, 320), (736, 794), user)

    @commands.command(name="autism2")
    async def autism2(self, ctx: commands.Context, user: commands.MemberConverter=None) -> None:
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
        await self._composite_images(ctx, "autism2.jpg", [(73, 73), (73, 73), (46, 46)], [(15, 1), (15, 551), (123, 709)], user, text=_txt)

    @commands.command(name="fatfuck")
    async def fatfuck(self, ctx: commands.Context, user: commands.MemberConverter=None) -> None:
        """https://i.imgur.com/Vbkfu4u.jpg"""
        await self._composite_images(ctx, "fatfuck.jpg", (385, 385), (67, 0), user)