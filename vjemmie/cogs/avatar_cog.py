import io
from itertools import zip_longest
from typing import List, Tuple, Union
from unidecode import unidecode
from dataclasses import dataclass

import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont, ImageFilter

from .base_cog import BaseCog
from ..utils.converters import MemberOrURLConverter


@dataclass
class Avatar: # Should be a collections.namedtuple or typing.NamedTuple instead tbh
    """Size and position of a user's avatar."""
    w: int # Width
    h: int # Height
    x: int # X Position
    y: int # Y Position


@dataclass
class Text:
    """Represents text to be added to an image. 
    Attributes correspond with parameters of AvatarCog._add_text()`
    """
    content: str
    size: int
    offset: Tuple[int, int] # x, y
    font: str
    color: Tuple[int, int, int, int] # RGBA
    shadow: bool = False
  

class AvatarCog(BaseCog):
    """Create images featuring a user's avatar."""
    
    EMOJI = ":person_frowning:"

    async def _composite_images(self,
                             ctx: commands.Context,
                             template: str,
                             avatars: List[Avatar],
                             user: MemberOrURLConverter=None, # I suppose this could just be Union[str, discord.Member]
                             text: List[Text]=None,
                             template_overlay: bool=False) -> None:
        """Creates a composite image of a user's avatar and a given template.
        
        Parameters
        ----------
        ctx : `commands.Context`
            Discord Context object
        
        template : `str`
            File name of image to be used as template. 
            Must be located in memes/templates/
        
        avatars : `List[Avatar]`
            List of objects describing avatar size and position.
            For each object in list, an avatar with the specified size
            and position is added to the final image.

        user : `commands.MemberConverter`, optional
            A Discord user. If specified, this user's avatar is 
            downloaded in place of the message author's.
        
        text : `List[Text]`, optional
            List of Text objects, whose attributes correspond with 
            `AvatarCog._add_text()` parameters.
        
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
        background = await self._do_paste(background, avatar, avatars, template_overlay)

        # Add text
        if text:
            for txt in text:
                background = await self._add_text(ctx, background, **txt.__dict__)

        # Save image to file-like object
        result = io.BytesIO()
        background.save(result, format="PNG")
        result.seek(0) # Seek to byte 0, so discord.File can use BytesIO.read()

        # Upload image to discord and get embed
        embed = await self.get_embed_from_img_upload(ctx, result, "out.png")
        await ctx.send(embed=embed)
    
    async def _resize_paste(
                        self, 
                        background: Image.Image, 
                        overlay: Image.Image, 
                        avatar: Avatar
                    ) -> Image.Image:
        """Resizes an image (param `overlay`) and pastes it onto another
        image (param `background`)

        Parameters
        ----------
        background : `Image.Image`
            Image that will have overlay pasted to it
        overlay : `Image.Image`
            Image to paste on to background
        avatar: `Avatar`
            Dimensions and position of avatar to paste.
        
        Returns
        -------
        `Image.Image`
            Image background with Image overlay pasted on top of it
        """
        overlay = overlay.resize((avatar.w, avatar.h), resample=Image.BICUBIC)
        background.paste(overlay, (avatar.x, avatar.y), overlay.convert("RGBA"))
        return background 
    
    async def _do_paste(self, 
                  background: Image.Image, 
                  user_avatar: Image.Image, 
                  avatars: List[Avatar],
                  template_overlay: bool) -> Image.Image:
        # Paste user avatars
        for av in avatars:
            # Template goes on top of image
            if template_overlay:
                new = Image.new("RGBA", background.size)
                new = await self._resize_paste(new, user_avatar, av)
                background = Image.alpha_composite(new, background)
            else: # Image goes on top of template
                background = await self._resize_paste(background, user_avatar, av)
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
        await self._composite_images(
            ctx, 
            template="nasa.jpg", 
            avatars=[Avatar(w=100, h=100, x=347, y=403)], 
            user=user
        )

    @commands.command(name="northkorea", aliases=["nk"])
    async def northkorea(self, ctx: commands.Context, user: MemberOrURLConverter=None) -> None:
        """https://i.imgur.com/PiqzXNs.jpg"""
        await self._composite_images(
            ctx, 
            template="northkorea1.jpg",
            avatars=[Avatar(w=295, h=295, x=712, y=195)],
            user=user
        )

    @commands.command(name="cancer", aliases=["cer"])
    async def cancer(self, ctx: commands.Context, user: MemberOrURLConverter=None) -> None:
        """https://i.imgur.com/vDtktIq.jpg"""
        await self._composite_images(
            ctx, 
            template="cancer.jpg", 
            avatars=[Avatar(w=762, h=740, x=772, y=680)], 
            user=user
        )

    @commands.command(name="mlady", aliases=["neckbeard"])
    async def mlady(self, ctx: commands.Context, user: MemberOrURLConverter=None) -> None:
        """https://i.imgur.com/2LQkErQ.png"""
        await self._composite_images(
            ctx, 
            template="mlady.png",
            avatars=[Avatar(w=275, h=275, x=86, y=78)], 
            user=user, 
            template_overlay=True
        )
    
    @commands.command(name="mlady2", aliases=["neckbeard2"])
    async def mlady2(self, ctx: commands.Context, user: MemberOrURLConverter=None) -> None:
        """https://i.imgur.com/2LQkErQ.png"""
        await self._composite_images(
            ctx, 
            template="mlady2.png", 
            avatars=[Avatar(w=200, h=200, x=161, y=101)], 
            user=user, 
            template_overlay=True
        )

    @commands.command(name="loud", aliases=["loudest"])
    async def loud(self, ctx: commands.Context, user: MemberOrURLConverter=None) -> None:
        """https://i.imgur.com/y7y7MRt.jpg"""
        await self._composite_images(
            ctx, 
            template="loud.jpg", 
            avatars=[Avatar(w=190, h=190, x=556, y=445)], 
            user=user
        )

    @commands.command(name="guys", aliases=["guyswant"])
    async def guys_only_want_one_thing(self, ctx: commands.Context, user: MemberOrURLConverter=None) -> None:
        """https://i.imgur.com/5oUe8VN.jpg"""
        await self._composite_images(
            ctx, 
            template="guyswant.jpg", 
            avatars=[Avatar(w=400, h=400, x=121, y=347)], 
            user=user
        )

    @commands.command(name="furry")
    async def furry(self, ctx: commands.Context, user: MemberOrURLConverter=None) -> None:
        """https://i.imgur.com/Jq3uu02.png"""
        await self._composite_images(
            ctx, 
            template="furry.png", 
            avatars=[Avatar(w=230, h=230, x=26, y=199)], 
            user=user, 
            template_overlay=True
        )

    @commands.command(name="autism", aliases=["thirtyseven"])
    async def autism(self, ctx: commands.Context, user: MemberOrURLConverter=None) -> None:
        """https://i.imgur.com/HcjIbpP.jpg"""
        await self._composite_images(
            ctx, 
            template="autism.jpg", 
            avatars=[Avatar(w=303, h=255, x=0, y=512)], 
            user=user
        )

    @commands.command(name="disabled")
    async def disabled(self, ctx: commands.Context, user: MemberOrURLConverter=None) -> None:
        """https://i.imgur.com/hZSghxu.jpg"""
        await self._composite_images(
            ctx, 
            template="disabled.jpg", 
            avatars=[Avatar(w=320, h=320, x=736, y=794)], 
            user=user
        )

    @commands.command(name="autism2")
    async def autism2(self, ctx: commands.Context, user: MemberOrURLConverter=None) -> None:
        """https://i.imgur.com/6lxlqPk.jpg"""
        text1 = Text(
            content=user.name if user else ctx.message.author.name,
            size=20,
            offset=(96, 0),
            font="LiberationSans-Regular.ttf",
            color=(0, 0, 0, 255)
        )
        text2 = Text(**text1.__dict__)
        text2.offset = (96, 551)

        await self._composite_images(
            ctx, 
            template="autism2.jpg", 
            avatars = [
                Avatar(w=73, h=73, x=15, y=1), 
                Avatar(w=73, h=73, x=15, y=551),
                Avatar(w=46, h=46, x=123, y=709)
            ],
            user=user, 
            text=[text1, text2]
        )

    @commands.command(name="fatfuck")
    async def fatfuck(self, ctx: commands.Context, user: MemberOrURLConverter=None) -> None:
        """https://i.imgur.com/Vbkfu4u.jpg"""
        await self._composite_images(
            ctx, 
            template="fatfuck.jpg", 
            avatars=[Avatar(w=385, h=385, x=67, y=0)],
            user=user
        )

    @commands.command(name="saxophone")
    async def saxophone(self, ctx: commands.Context, user: MemberOrURLConverter=None) -> None:
        """https://i.imgur.com/Gfw036Q.png"""
        await self._composite_images(
            ctx, 
            template="saxophone.png", 
            avatars=[
                Avatar(w=366, h=358, x=0, y=0), 
                Avatar(w=366, h=358, x=0, y=361)
            ],
            user=user,
            template_overlay=True
        )

    @commands.command(name="fingercircle")
    async def fingercircle(self, ctx: commands.Context, user: MemberOrURLConverter=None) -> None:
        """https://i.imgur.com/HnpJkvB.jpg"""
        await self._composite_images(
            ctx, 
            template="fingercircle.jpg", 
            avatars=[Avatar(w=251, h=278, x=317, y=20)],
            user=user
        )
    
    @commands.command(name="lordofthepit")
    async def lordofthepit(self, ctx: commands.Context, user: MemberOrURLConverter=None) -> None:
        """https://i.imgur.com/IRntn02.jpg"""
        await self._composite_images(
            ctx, 
            template="lordofthepit.jpg", 
            avatars=[Avatar(w=559, h=410, x=57, y=110)],
            user=user
        )

    @commands.command(name="bigounce")
    async def bigounce(self, ctx: commands.Context, user: MemberOrURLConverter=None) -> None:
        """https://i.imgur.com/apDeSO6.jpg"""
        await self._composite_images(
            ctx, 
            template="bigounce.png", 
            avatars=[Avatar(w=504, h=504, x=0, y=0)], 
            user=user, 
            template_overlay=True
        )

    @commands.command(name="bigounce2")
    async def bigounce2(self, ctx: commands.Context, user: MemberOrURLConverter=None) -> None:
        """https://i.imgur.com/apDeSO6.jpg with username"""
        uname = user.name if user else ctx.message.author.name
        text = Text(
            content=unidecode(uname).upper(),
            size=31,
            offset=(194, 431),
            font="Cocogoose Pro-trial.ttf",
            color=(234, 246, 247, 255),
            shadow=True
        )
        await self._composite_images(
            ctx, 
            template="bigounce2.png", 
            avatars=[Avatar(w=504, h=504, x=0, y=0)], 
            user=user, 
            template_overlay=True, 
            text=[text]
        )