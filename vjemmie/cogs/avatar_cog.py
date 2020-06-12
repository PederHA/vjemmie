import io
from itertools import zip_longest
from typing import List, Tuple, Union
from unidecode import unidecode

import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont, ImageFilter

from .base_cog import BaseCog
from ..utils.converters import MemberOrURLConverter


class AvatarCog(BaseCog):
    """Create images featuring a user's avatar."""
    
    EMOJI = ":person_frowning:"

    async def _composite_images(self,
                             ctx: commands.Context,
                             template: str,
                             resize:List[Tuple[int, int]],
                             offset:List[Tuple[int, int]],
                             user: MemberOrURLConverter=None, # I suppose this could just be Union[str, discord.Member]
                             text: List[dict]=None,
                             template_overlay: bool=False) -> None:
        """Creates a composite image of a user's avatar and a given template.
        
        Parameters
        ----------
        ctx : `commands.Context`
            Discord Context object
        
        template : `str`
            File name of image to be used as template. 
            Must be located in memes/templates/
        
        resize : `List[Tuple[int, int]]`
            List of tuples (width, height). Multiple tuples
            indicate that multiple instances of a user's avatar is 
            to be added to the template image.
        
        offset : `List[Tuple[int, int]]`
            List of tuples (x_position, y_position).
            Same logic as `resize` with regards to lists.
        
        user : `commands.MemberConverter`, optional
            A Discord user. If specified, this user's avatar is 
            downloaded in place of the message author's.
        
        text : `List[dict]`, optional
            List of kwargs corresponding to `ImageCog._add_text()` parameters.
        
        template_overlay : `bool`, optional
            If True, the order of template and avatar is reversed, 
            and the template is placed over the avatar.
        """
        # Use message author's avatar if no user is specified
        if not user:
            avatar_url = ctx.message.author.avatar_url # remove ?size=1024 suffix since a lower res image danker anyway
        elif isinstance(user, discord.Member):
            avatar_url = user.avatar_url
        elif isinstance(user, str):
            avatar_url = user
        else:
            raise TypeError("Argument 'user' must be type 'discord.User' or an image URL of type 'str'")
        
        if isinstance(avatar_url, discord.asset.Asset):
            _avatar = io.BytesIO(await avatar_url.read())
        else:
            _avatar = await self.download_from_url(ctx, avatar_url)

        avatar = Image.open(_avatar)
        background = Image.open(f"memes/templates/{template}", "r")

        # Convert template to RGBA
        if background.mode == "RGB":
            background.putalpha(255) # puts an alpha channel on the image

        # Add avatar to template
        background = await self._do_paste(background, avatar, resize, offset, template_overlay)

        # Add text
        if text:
            for txt in text:
                background = await self._add_text(ctx, background, **txt)

        # Save image to file-like object
        result = io.BytesIO()
        background.save(result, format="PNG")
        result.seek(0) # Seek to byte 0, so discord.File can use BytesIO.read()

        # Upload image to discord and get embed
        embed = await self.get_embed_from_img_upload(ctx, result, "out.png")
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
                  resize: List[Tuple[int, int]], 
                  offset: List[Tuple[int, int]],
                  template_overlay: bool) -> Image.Image:
        # Fill with first value of shortest list if number of elements are not identical
        fill_value = max(resize, offset)[0] if len(resize) != len(offset) else None
        # Paste user avatars
        for off, rsz in zip_longest(offset, resize, fillvalue=fill_value):
            # Template goes on top of image
            if template_overlay:
                new = Image.new("RGBA", background.size)
                new = await self._resize_paste(new, user_avatar, rsz, off)
                background = Image.alpha_composite(new, background)
            else: # Image goes on top of template
                background = await self._resize_paste(background, user_avatar, rsz, off)
        # FIXME: Potentially undefined variable error here if len(offset) + len(resize) == 0
        return background 

    async def _add_text(self,
                        ctx: commands.Context,
                        background: Image.Image,
                        font: str = None,
                        size: int = 20,
                        offset: Tuple[int, int] = (0, 0),
                        color: Tuple[int, int, int, int] = (255, 255, 255, 255),
                        shadow: bool = False,
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
        
        # Drop shadow
        if shadow:
            _shadow = Image.new("RGBA", background.size)
            s = ImageDraw.Draw(_shadow)
            s.text(
                (
                    # Offset + 1% of width/height of image
                    offset[0]+(background.size[0]//100), 
                    offset[1]+(background.size[1]//100)
                ), 
                content, 
                font=font, 
                fill=(0, 0, 0, 92)
            )
            _shadow = _shadow.filter(ImageFilter.BLUR)
            _txt = Image.alpha_composite(_txt, _shadow)

        # Get a drawing context
        d = ImageDraw.Draw(_txt)
        d.text(offset, content, font=font, fill=color)

        # Return alpha composite of background and text
        return Image.alpha_composite(background, _txt)

    @commands.command(name="fuckup", aliases=["nasa"])
    async def nasa(self, ctx: commands.Context, user: MemberOrURLConverter=None) -> None:
        """https://i.imgur.com/HcjIbpP.jpg"""
        await self._composite_images(ctx, "nasa.jpg", [(100, 100)], [(347, 403)], user)

    @commands.command(name="northkorea", aliases=["nk"])
    async def northkorea(self, ctx: commands.Context, user: MemberOrURLConverter=None) -> None:
        """https://i.imgur.com/PiqzXNs.jpg"""
        await self._composite_images(ctx, "northkorea1.jpg", [(295, 295)], [(712, 195)], user)

    @commands.command(name="cancer", aliases=["cer"])
    async def cancer(self, ctx: commands.Context, user: MemberOrURLConverter=None) -> None:
        """https://i.imgur.com/vDtktIq.jpg"""
        await self._composite_images(ctx, "cancer.jpg", [(762, 740)], [(772, 680)], user)

    @commands.command(name="mlady", aliases=["neckbeard"])
    async def mlady(self, ctx: commands.Context, user: MemberOrURLConverter=None) -> None:
        """https://i.imgur.com/2LQkErQ.png"""
        await self._composite_images(ctx, "mlady.png", [(275, 275)], [(86, 78)], user, template_overlay=True)
    
    @commands.command(name="mlady2", aliases=["neckbeard2"])
    async def mlady2(self, ctx: commands.Context, user: MemberOrURLConverter=None) -> None:
        """https://i.imgur.com/2LQkErQ.png"""
        await self._composite_images(ctx, "mlady2.png", [(200, 200)], [(161, 101)], user, template_overlay=True)

    @commands.command(name="loud", aliases=["loudest"])
    async def loud(self, ctx: commands.Context, user: MemberOrURLConverter=None) -> None:
        """https://i.imgur.com/y7y7MRt.jpg"""
        await self._composite_images(ctx, "loud.jpg", [(190, 190)], [(556, 445)], user)

    @commands.command(name="guys", aliases=["guyswant"])
    async def guys_only_want_one_thing(self, ctx: commands.Context, user: MemberOrURLConverter=None) -> None:
        """https://i.imgur.com/5oUe8VN.jpg"""
        await self._composite_images(ctx, "guyswant.jpg", [(400, 400)], [(121, 347)], user)

    @commands.command(name="furry")
    async def furry(self, ctx: commands.Context, user: MemberOrURLConverter=None) -> None:
        """https://i.imgur.com/Jq3uu02.png"""
        await self._composite_images(ctx, "furry.png", [(230, 230)], [(26, 199)], user, template_overlay=True)

    @commands.command(name="autism", aliases=["thirtyseven"])
    async def autism(self, ctx: commands.Context, user: MemberOrURLConverter=None) -> None:
        """https://i.imgur.com/HcjIbpP.jpg"""
        await self._composite_images(ctx, "autism.jpg", [(303, 255)], [(0, 512)], user)

    @commands.command(name="disabled")
    async def disabled(self, ctx: commands.Context, user: MemberOrURLConverter=None) -> None:
        """https://i.imgur.com/hZSghxu.jpg"""
        await self._composite_images(ctx, "disabled.jpg", [(320, 320)], [(736, 794)], user)

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
        await self._composite_images(ctx, "fatfuck.jpg", [(385, 385)], [(67, 0)], user)

    @commands.command(name="saxophone")
    async def saxophone(self, ctx: commands.Context, user: MemberOrURLConverter=None) -> None:
        """https://i.imgur.com/Gfw036Q.png"""
        await self._composite_images(ctx, "saxophone.png", [(366, 358)], [(0, 0), (0, 361)], user, template_overlay=True)

    @commands.command(name="fingercircle")
    async def fingercircle(self, ctx: commands.Context, user: MemberOrURLConverter=None) -> None:
        """https://i.imgur.com/HnpJkvB.jpg"""
        await self._composite_images(ctx, "fingercircle.jpg", [(251, 278)], [(317, 20)], user)
    
    @commands.command(name="lordofthepit")
    async def lordofthepit(self, ctx: commands.Context, user: MemberOrURLConverter=None) -> None:
        """https://i.imgur.com/IRntn02.jpg"""
        await self._composite_images(ctx, "lordofthepit.jpg", [(559, 410)], [(57, 110)], user)

    @commands.command(name="bigounce")
    async def bigounce(self, ctx: commands.Context, user: MemberOrURLConverter=None) -> None:
        """https://i.imgur.com/apDeSO6.jpg"""
        await self._composite_images(ctx, "bigounce.png", [(504, 504)], [(0, 0)], user, template_overlay=True)

    @commands.command(name="bigounce2")
    async def bigounce2(self, ctx: commands.Context, user: MemberOrURLConverter=None) -> None:
        """https://i.imgur.com/apDeSO6.jpg with username"""
        uname = user.name if user else ctx.message.author.name
        text = {
            "content": unidecode(uname).upper(),
            "size": 31,
            "offset": (194, 431),
            "font": "Cocogoose Pro-trial.ttf",
            "color": (234, 246, 247, 255),
            "shadow": True
        }
        await self._composite_images(ctx, "bigounce2.png", [(504, 504)], [(0, 0)], user, template_overlay=True, text=[text])