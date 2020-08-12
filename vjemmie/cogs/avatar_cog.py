from __future__ import annotations

import io
from itertools import zip_longest
from typing import List, Tuple, Union, Optional, Callable
from unidecode import unidecode
from dataclasses import dataclass, field
from pathlib import Path
from copy import deepcopy

import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont, ImageFilter

from .base_cog import BaseCog
from ..utils.converters import NonCaseSensMemberConverter, MemberOrURLConverter
from ..utils.commands import add_command
from ..utils.exceptions import CommandError


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
    
    `content` always defaults to ctx.message.author.name or user.name if
    not given a value.
    """
    
    size: int
    offset: Tuple[int, int] # x, y
    content: str = ""
    font: str = "LiberationSans-Regular.ttf"
    color: Tuple[int, int, int, int] = (255, 255, 255, 255) # RGBA 
    shadow: bool = False
    stroke: bool = False
    stroke_thickness: int = 1
    stroke_color: Tuple[int, int, int, int] = (0, 0, 0, 255)
    upper: bool = False
    center: bool = False # Center text horizontally
    size_func: Optional[Callable[[Text], int]] = None

    def __post_init__(self) -> None:
        # TODO: Check that font exists
        # Check that parameters are correctly formatted and values are within acceptable ranges
        pass


@dataclass
class AvatarCommand:
    name: str
    template: Union[Path, str]
    avatars: List[Avatar]
    help: Optional[str] = None
    aliases: List[str] = field(default_factory=list)
    text: List[Text] = field(default_factory=list)
    template_overlay: bool = False


avatar_commands = [
    AvatarCommand(
        name="fuckup",
        aliases=["nasa"],
        template="nasa.jpg",
        help="https://i.imgur.com/xWlh36n.jpg",
        avatars=[Avatar(w=100, h=100, x=347, y=403)]
    ),
    AvatarCommand(
        name="cancer",
        template="cancer.jpg",
        help="https://i.imgur.com/vDtktIq.jpg",
        avatars=[Avatar(w=762, h=740, x=772, y=680)], 
    ),
    AvatarCommand(
        name="northkorea",
        template="northkorea1.jpg",
        help="https://i.imgur.com/PiqzXNs.jpg",
        avatars=[Avatar(w=295, h=295, x=712, y=195)],
    ),
    AvatarCommand(
        name="mlady",
        template="mlady.png",
        help="https://i.imgur.com/2LQkErQ.png",
        avatars=[Avatar(w=275, h=275, x=86, y=78)], 
        template_overlay=True
    ),
    AvatarCommand(
        name="mlady2",
        template="mlady2.png",
        help="https://i.imgur.com/2LQkErQ.png",
        avatars=[Avatar(w=200, h=200, x=161, y=101)], 
        template_overlay=True
    ),
    AvatarCommand(
        name="loud",
        template="loud.jpg",
        help="https://i.imgur.com/y7y7MRt.jpg",
        avatars=[Avatar(w=190, h=190, x=556, y=445)],  
    ),
    AvatarCommand(
        name="guys",
        template="guyswant.jpg",
        help="https://i.imgur.com/5oUe8VN.jpg",
        avatars=[Avatar(w=400, h=400, x=121, y=347)], 
    ),
    AvatarCommand(
        name="furry",
        template="furry.png",
        help="https://i.imgur.com/Jq3uu02.png",
        avatars=[Avatar(w=230, h=230, x=26, y=199)], 
        template_overlay=True
    ),
    AvatarCommand(
        name="autism",
        template="autism.jpg",
        help="https://i.imgur.com/HcjIbpP.jpg",
        avatars=[Avatar(w=303, h=255, x=0, y=512)],
    ),
    AvatarCommand(
        name="autism2",
        template="autism2.jpg",
        help="https://i.imgur.com/6lxlqPk.jpg",
        avatars=[
            Avatar(w=73, h=73, x=15, y=1), 
            Avatar(w=73, h=73, x=15, y=551),
            Avatar(w=46, h=46, x=123, y=709)
        ],
        text=[
            Text(
                size=20,
                offset=(96, 0),
                font="LiberationSans-Regular.ttf",
                color=(0, 0, 0, 255)
            ),
            Text(
                size=20,
                offset=(96, 551),
                font="LiberationSans-Regular.ttf",
                color=(0, 0, 0, 255)
            )  
        ], 
    ),
    AvatarCommand(
        name="disabled",
        template="disabled.jpg",
        help="https://i.imgur.com/hZSghxu.jpg",
        avatars=[Avatar(w=320, h=320, x=736, y=794)],
    ),
    AvatarCommand(
        name="fatfuck",
        template="fatfuck.jpg",
        help="https://i.imgur.com/Vbkfu4u.jpg",
        avatars=[Avatar(w=385, h=385, x=67, y=0)],
    ),
    AvatarCommand(
        name="saxophone",
        template="saxophone.png",
        help="https://i.imgur.com/Gfw036Q.png",
        avatars=[
            Avatar(w=366, h=358, x=0, y=0), 
            Avatar(w=366, h=358, x=0, y=361)
        ],
        template_overlay=True
    ),
    AvatarCommand(
        name="fingercircle",
        template="fingercircle.jpg",
        help="https://i.imgur.com/HnpJkvB.jpg",
        avatars=[Avatar(w=251, h=278, x=317, y=20)],
    ),
    AvatarCommand(
        name="lordofthepit",
        template="lordofthepit.jpg",
        help="https://i.imgur.com/IRntn02.jpg",
        avatars=[Avatar(w=559, h=410, x=57, y=110)],
    ),
    AvatarCommand(
        name="bigounce",
        template="bigounce.png",
        help="https://i.imgur.com/apDeSO6.jpg",
        avatars=[Avatar(w=504, h=504, x=0, y=0)], 
        template_overlay=True
    ),
    AvatarCommand(
        name="bigounce2",
        template="bigounce2.png",
        help="https://i.imgur.com/apDeSO6.jpg",
        avatars=[Avatar(w=504, h=504, x=0, y=0)], 
        template_overlay=True,
        text=[
            Text(
                size=31,
                offset=(194, 431),
                font="Cocogoose Pro-trial.ttf",
                color=(234, 246, 247, 255),
                shadow=True,
                upper=True
            )
        ]
    ),
    AvatarCommand(
        name="allmyhomies",
        template="allmyhomies.jpg",
        help="https://i.imgur.com/7jxk8Qd.jpg",
        avatars=[Avatar(w=200, h=200, x=260, y=205)], 
        #template_overlay=True, # hide avatar
        text=[
            Text(
                size=70,
                offset=(319, 15),
                font="Cocogoose Pro-trial.ttf",
                color=(237, 221, 208, 255),
                shadow=True,
                stroke=True,
                stroke_thickness=3,
                upper=True,
                size_func=(
                    lambda t: 630 // len(t.content)
                ),
            ),
            Text(
                size=80,
                offset=(160, 560),
                font="Cocogoose Pro-trial.ttf",
                color=(237, 221, 208, 255),
                shadow=True,
                stroke=True,
                stroke_thickness=3,
                upper=True,
                center=True
            )
        ]
    ),
]


async def avatar_command(cog: commands.Cog, ctx: commands.Context, user: NonCaseSensMemberConverter=None, *, command: AvatarCommand) -> None:
    # NOTE: Handle this somewhere else?
    cmd = deepcopy(command) # so we can modify command attributes locally
    for text in cmd.text:
        if not text.content:
            text.content = unidecode(user.name if user else ctx.message.author.name)
    await cog.make_composite_image(
        ctx, 
        command=cmd,
        user=user,
    )    


class AvatarCog(BaseCog):
    """Create images featuring a user's avatar."""
    
    EMOJI = ":person_frowning:"

    def __init__(self, bot: commands.Bot) -> None:
        super().__init__(bot)
        self.add_avatar_commands()
    
    def add_avatar_commands(self) -> None:
        for command in avatar_commands:
            add_command(
                self, 
                avatar_command, 
                name=command.name, 
                aliases=command.aliases,
                help=command.help,
                command=command
            )
    
    async def make_composite_image(
                            self,
                            ctx: commands.Context,
                            command: AvatarCommand,
                            user: Optional[discord.Member]=None,
                            ) -> None:
        """Creates a composite image of a user's avatar and a given template.
        
        Parameters
        ----------
        ctx : `commands.Context`
            Discord Context object 
        
        command : `AvatarCommand`
            TODO: Description
        
        user : `discord.Member`, optional
            A Discord user. If specified, this user's avatar is 
            downloaded in place of the message author's.
        """
        # Use message author's avatar if no user is specified
        if not user:
            avatar_url = ctx.message.author.avatar_url
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

        result = await self.bot.loop.run_in_executor(
            None, 
            self._do_make_composite_image, 
            command,
            _avatar
        )
        embed = await self.get_embed_from_img_upload(ctx, result, "out.png")
        await ctx.send(embed=embed)
    
    def _do_make_composite_image(self, command: AvatarCommand, byteavatar: io.BytesIO) -> io.BytesIO:
        avatar = Image.open(byteavatar)
        tpath = Path(f"memes/templates/{command.template}")
        if not tpath.exists():
            raise CommandError(f"Template {command.template}")
        background = Image.open(tpath, "r")

        # Convert template to RGBA
        if background.mode == "RGB":
            background.putalpha(255) # puts an alpha channel on the image

        # Add avatar to template
        background = self._add_avatar(background, avatar, command.avatars, command.template_overlay)

        # Add text
        for txt in command.text:
            background = self._add_text(background, txt)

        # Save image to file-like object
        result = io.BytesIO()
        background.save(result, format="PNG")
        result.seek(0) # Seek to byte 0, so discord.File can use BytesIO.read()
        return result        

    def _resize_paste(
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
    
    def _add_avatar(self, 
                  background: Image.Image, 
                  user_avatar: Image.Image, 
                  avatars: List[Avatar],
                  template_overlay: bool) -> Image.Image:
        # Paste user avatars
        for av in avatars:
            # Template goes on top of image
            if template_overlay:
                new = Image.new("RGBA", background.size)
                new = self._resize_paste(new, user_avatar, av)
                background = Image.alpha_composite(new, background)
            else: # Image goes on top of template
                background = self._resize_paste(background, user_avatar, av)
        return background 

    def _add_text(self,
                        background: Image.Image,
                        text: Text
                       ) -> Image.Image:
        """Adds text to an image by creating an alpha composite of a given
        image and one or more generated lines of text.
        
        Parameters
        ----------
        background : `Image.Image`
            Image to be modified
        text : `Text`
            Text to add on to image
        
        Returns
        -------
        `Image.Image`
            A composite of image `background` and generated text
        """
        if text.upper:
            text.content = text.content.upper()
        
        if text.size_func:
            text.size = text.size_func(text)

        # Get new image
        _txt = Image.new("RGBA", background.size)
        # Get font
        font = ImageFont.truetype(f"memes/fonts/{text.font}", text.size)
        
        # Drop shadow
        if text.shadow:
            _shadow = Image.new("RGBA", background.size)
            s = ImageDraw.Draw(_shadow)
            s.text(
                (
                    # Offset + 1% of width/height of image
                    # TODO: If result of integer divison is 0,
                    #       set value to 1.
                    text.offset[0]+(background.size[0]//100), 
                    text.offset[1]+(background.size[1]//100)
                ), 
                text.content, 
                font=font, 
                fill=(0, 0, 0, 92)
            )
            _shadow = _shadow.filter(ImageFilter.BLUR)
            _txt = Image.alpha_composite(_txt, _shadow)
        
        # Get a drawing context
        d = ImageDraw.Draw(_txt)

        # Centering determines the value of the offset variable
        if text.center:
            w, _ = d.textsize(text.content, font=font)
            img_w, _ = background.size
            offset = ((img_w-w)/2, text.offset[1]) # how ugly is this dude
        else: 
            offset = text.offset

        # Add stroke FIRST
        if text.stroke:
            t = text.stroke_thickness
            d.text((offset[0]-t, offset[1]-t), text.content, font=font, fill=text.stroke_color)
            d.text((offset[0]+t, offset[1]-t), text.content, font=font, fill=text.stroke_color)
            d.text((offset[0]-t, offset[1]+t), text.content, font=font, fill=text.stroke_color)
            d.text((offset[0]+t, offset[1]+t), text.content, font=font, fill=text.stroke_color)
        
        d.text(offset, text.content, font=font, fill=text.color)

        # Return alpha composite of background and text
        return Image.alpha_composite(background, _txt)
