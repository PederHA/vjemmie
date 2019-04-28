import io
from itertools import zip_longest
from typing import List, Tuple, Union

import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont

from cogs.base_cog import BaseCog
from ext.converters import MemberOrURLConverter


class AvatarCog(BaseCog):
    """Create images featuring a user's avatar."""
    
    EMOJI = ":person_frowning:"

    async def _composite_images(self,
                             ctx: commands.Context,
                             template: str,
                             resize:Union[Tuple[int,int], list],
                             offset:Union[Tuple[int,int], list],
                             user: MemberOrURLConverter=None, # I suppose this could just be Union[str, discord.Member]
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
        # Use message author's avatar if no user is specified
        if not user:
            user_avatar_url = ctx.message.author.avatar_url._url.split("?")[0] # remove ?size=1024 suffix since a lower res image danker anyway
        elif isinstance(user, discord.Member):
            user_avatar_url = user.avatar_url._url
        elif isinstance(user, str):
            user_avatar_url = user

        # Download user's avatar
        with open("memes/temp/temp.webp", "wb") as f:
            avatar_img = await self.download_from_url(ctx, user_avatar_url)
            f.write(avatar_img.read())

        # Open user's avatar
        user_avatar = Image.open("memes/temp/temp.webp", "r")

        # Open template
        background = Image.open(f"memes/templates/{template}", "r")

        # Convert template to RGBA
        if background.mode == "RGB":
            background.putalpha(255) # puts an alpha channel on the image

        # Add avatar to template
        background = await self._do_paste(background, user_avatar, resize, offset, template_overlay)

        # Add text
        if text:
            if isinstance(text, dict):
                background = await self._add_text(ctx, background, **text)
            elif isinstance(text, list):
                for txt in text:
                    background = await self._add_text(ctx, background, **txt)

        # Save image to file-like object
        file_like_obj = io.BytesIO()
        background.save(file_like_obj, format="PNG")
        file_like_obj.seek(0) # Seek to byte 0, so discord.File can use BytesIO.read()

        # Upload image to discord and get embed
        embed = await self.get_embed_from_img_upload(ctx, file_like_obj, "out.png")
        await ctx.send(embed=embed)
    
    async def _resize_paste(self, 
                      background: Image.Image, 
                      overlay: Image.Image, 
                      resize: Tuple[int, int], 
                      offset: Tuple[int, int]) -> Image.Image:
        """Resizes an image `overlay` and pastes it to `background`

        NOTE
        ----
        Generally, type of arguments to parameters `resize` and `offset`
        should be identical to avoid unintended results. However, there are
        protections in place if types do not match.
        
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
        background.paste(overlay, offset, overlay.convert("RGBA"))
        return background 
    
    async def _do_paste(self, 
                  background: Image.Image, 
                  user_avatar: Image.Image, 
                  resize: Union[tuple, list], 
                  offset: Union[tuple, list],
                  template_overlay: bool) -> Image.Image:
        # Paste a single copy of user's avatar if argument offset is a single (x, y) offset tuple
        if isinstance(offset, tuple):
            # Choose first list index item if resize is type list
            if isinstance(resize, list):
                resize = resize[0]
            if not template_overlay:
                background = await self._resize_paste(background, user_avatar, resize, offset)
            else:
                new = Image.new("RGBA", background.size)
                new = await self._resize_paste(new, user_avatar, resize, offset)
                background = Image.alpha_composite(new, background)                    
        
        # Paste multiple copies of user's avatar if argument offset is a list of (x, y) offset tuples
        elif isinstance(offset, list):
            if not isinstance(resize, list):
                # Create list of tuples of size n=len(offset) if resize is not type(list)
                resize = [resize]*len(offset)
            # Fill with first value of shortest list if number of elements are not identical
            fill_value = max(resize, offset)[0] if len(resize) != len(offset) else None
            # Paste user avatars
            for off, rsz in zip_longest(offset, resize, fillvalue=fill_value):
                if not template_overlay:
                    background = await self._resize_paste(background, user_avatar, rsz, off)
                else:
                    new = Image.new("RGBA", background.size)
                    new = await self._resize_paste(new, user_avatar, rsz, off)
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
    async def nasa(self, ctx: commands.Context, user: MemberOrURLConverter=None) -> None:
        """https://i.imgur.com/HcjIbpP.jpg"""
        await self._composite_images(ctx, "nasa.jpg", (100, 100), (347, 403), user)

    @commands.command(name="northkorea", aliases=["nk"])
    async def northkorea(self, ctx: commands.Context, user: MemberOrURLConverter=None) -> None:
        """https://i.imgur.com/PiqzXNs.jpg"""
        await self._composite_images(ctx, "northkorea1.jpg", (295, 295), (712, 195), user)

    @commands.command(name="cancer", aliases=["cer"])
    async def cancer(self, ctx: commands.Context, user: MemberOrURLConverter=None) -> None:
        """https://i.imgur.com/vDtktIq.jpg"""
        await self._composite_images(ctx, "cancer.jpg", (762, 740), (772, 680), user)

    @commands.command(name="mlady", aliases=["neckbeard"])
    async def mlady(self, ctx: commands.Context, user: MemberOrURLConverter=None) -> None:
        """https://i.imgur.com/2LQkErQ.png"""
        await self._composite_images(ctx, "mlady.png", (275, 275), (86, 78), user, template_overlay=True)
    
    @commands.command(name="mlady2", aliases=["neckbeard2"])
    async def mlady2(self, ctx: commands.Context, user: MemberOrURLConverter=None) -> None:
        """https://i.imgur.com/2LQkErQ.png"""
        await self._composite_images(ctx, "mlady2.png", (200, 200), (161, 101), user, template_overlay=True)

    @commands.command(name="loud", aliases=["loudest"])
    async def loud(self, ctx: commands.Context, user: MemberOrURLConverter=None) -> None:
        """https://i.imgur.com/y7y7MRt.jpg"""
        await self._composite_images(ctx, "loud.jpg", (190, 190), (556, 445), user)

    @commands.command(name="guys", aliases=["guyswant"])
    async def guys_only_want_one_thing(self, ctx: commands.Context, user: MemberOrURLConverter=None) -> None:
        """https://i.imgur.com/5oUe8VN.jpg"""
        await self._composite_images(ctx, "guyswant.jpg", (400, 400), (121, 347), user)

    @commands.command(name="furry")
    async def furry(self, ctx: commands.Context, user: MemberOrURLConverter=None) -> None:
        """https://i.imgur.com/Jq3uu02.png"""
        await self._composite_images(ctx, "furry.png", (230, 230), (26, 199), user, template_overlay=True)

    @commands.command(name="autism", aliases=["thirtyseven"])
    async def autism(self, ctx: commands.Context, user: MemberOrURLConverter=None) -> None:
        """https://i.imgur.com/HcjIbpP.jpg"""
        await self._composite_images(ctx, "autism.jpg", (303, 255), (0, 512), user)

    @commands.command(name="disabled")
    async def disabled(self, ctx: commands.Context, user: MemberOrURLConverter=None) -> None:
        """https://i.imgur.com/hZSghxu.jpg"""
        await self._composite_images(ctx, "disabled.jpg", (320, 320), (736, 794), user)

    @commands.command(name="autism2")
    async def autism2(self, ctx: commands.Context, user: MemberOrURLConverter=None) -> None:
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
    async def fatfuck(self, ctx: commands.Context, user: MemberOrURLConverter=None) -> None:
        """https://i.imgur.com/Vbkfu4u.jpg"""
        await self._composite_images(ctx, "fatfuck.jpg", (385, 385), (67, 0), user)

    @commands.command(name="saxophone")
    async def saxophone(self, ctx: commands.Context, user: MemberOrURLConverter=None) -> None:
        """https://i.imgur.com/Gfw036Q.png"""
        await self._composite_images(ctx, "saxophone.png", (366, 358), [(0, 0), (0, 361)], user, template_overlay=True)

    @commands.command(name="fingercircle")
    async def fingercircle(self, ctx: commands.Context, user: MemberOrURLConverter=None) -> None:
        """https://i.imgur.com/HnpJkvB.jpg"""
        await self._composite_images(ctx, "fingercircle.jpg", (251, 278), (317, 20), user)
    
    @commands.command(name="lordofthepit")
    async def lordofthepit(self, ctx: commands.Context, user: MemberOrURLConverter=None) -> None:
        """https://i.imgur.com/IRntn02.jpg"""
        await self._composite_images(ctx, "lordofthepit.jpg", (559, 410), (57, 110), user)

    @commands.command(name="oof")
    async def oof(self, ctx: commands.Context, user: MemberOrURLConverter=None) -> None:
        """https://i.imgur.com/V1CSHXa.jpg"""
        await self._composite_images(ctx, "oof.jpg", (531, 531), (0, 0), user)