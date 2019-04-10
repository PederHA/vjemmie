"""
Some frying methods in this module are based on https://github.com/asdvek/DeepFryBot,
but modified to fit into an OO design.

Original methods such as `add_text()` and `add_caption()` are added to provide
a richer set of functionality than what DeepFryBot provides.
"""

from PIL import Image, ImageDraw, ImageFont
import numpy as np
from random import randint
import requests
import shutil
from os import listdir
from typing import Iterable
import textwrap
from utils.exceptions import WordExceededLimit, NonImgURL, InvalidURL
import math
import io


class ImageFryer:
    def __init__(self, image: io.BytesIO):
        self.img = Image.open(image)
    
    @staticmethod
    async def get_files_in_dir(category: str) -> str:
        """
        This method was repurposed to work with an "all" filter, which lists
        both emojis and captions. To make this happen using the existing
        functionality of the method, a sort of hacky band-aid fix was put
        in place. It looks ugly, but it works for now.

        At the moment, this method suffers from god-awful variable names, 
        which might make its logic confusing at first glance.
        """
        HIDDEN = ["effects", "psd"]
        categories = [d for d in listdir("deepfryer/images") if d not in HIDDEN]
        
        if category not in categories:
            raise FileNotFoundError("No such image category")
        
        out = []
        for _file in listdir(f"deepfryer/images/{category}"):
            fname, ext = _file.split(".")
            out.append(fname)
        return "\n".join(out)

    def change_contrast(self, img: Image.Image, level:int=115) -> Image.Image:
        factor = (259 * (level + 255)) / (255 * (259 - level))
        def contrast(c):
            return 128 + factor * (c - 128)
        return img.point(contrast)

    def add_noise(self, img: Image.Image, factor:int=1) -> Image.Image:
        def noise(c):
            return c*(1+np.random.random(1)[0]*factor-factor/2)
        return img.point(noise)
    
    def add_emojis(self, img: Image.Image, emoji_name:str, limit: int=5):
        # create a temporary copy if img
        tmp = img.copy()
        default_emoji = 'b'
        minimum_limit = 2
        
        if limit < minimum_limit:
            limit = minimum_limit
        
        try:
            emoji = Image.open(f'deepfryer/images/emojis/{emoji_name.lower()}.png')
        except:
            emoji = Image.open(f"deepfryer/images/emojis/{default_emoji}.png")
        for i in range(0, randint(minimum_limit,limit)):
            # add selected emoji to random image coordinates
            coord = np.random.random(2)*np.array([img.width, img.height])
            resized = emoji.copy()
            size = int((img.width/10)*(np.random.random(1)[0]+1))
            resized.thumbnail((size, size), Image.ANTIALIAS)
            tmp.paste(resized, (int(coord[0]), int(coord[1])), resized)
        return tmp

    def add_caption(self, img: Image.Image, caption_name: str) -> Image.Image:
        """
        Adds a user-defined graphic on the bottom of the base image,
        that is stretched to fit the width of the image
        """
        tmp = img.copy()
        try:
            caption = Image.open(f'deepfryer/images/captions/{caption_name}.png')
        except:
            return img
        else:
            resized = caption.copy()
            # Coordinates of resized caption
            coord = (0, (img.height - caption.height))
            # Change caption width to match width of main image
            resized = resized.resize((img.width, caption.height))

            size = int((img.width)*(np.random.random(1)[0]+1))
            resized.thumbnail((size, size), Image.ANTIALIAS)
            
            # Paste resized caption to coordinates
            tmp.paste(resized, (int(coord[0]), int(coord[1])), resized)
            return tmp
    
    def add_text(self, img: Image.Image, text_string: str) -> Image.Image:
        """
        Adds text to an image based on a user-defined string. Text is placed
        on top of a white background. 

        Known issues:
        *   Currently adds the text ON TOP of the base image, rather 
            than adding it above the image, thereby causing the text 
            and its background to obscure parts of the image.
        """

        tmp = img.copy().convert("RGBA")

        # Create image to draw text on
        txt = Image.new("RGBA", tmp.size, (255,255,255,0))
        fnt = ImageFont.truetype(".deepfryer/fonts/LiberationSans-Regular.ttf", tmp.height//8)         
        d = ImageDraw.Draw(txt)
        
        # Split text into lines
        # Each character is aproximately 26 pixels
        lines = textwrap.wrap(text_string, width=(tmp.width//26.5))
        
        if len(lines) > 2:
            raise ValueError("Text string is too long!")

        
        # Draw text, limited to 2 lines
        y_text_pos = 0
        for line_count, line in enumerate(lines):
            if line_count < 2:
                width, height = fnt.getsize(line)
                d.text((0,y_text_pos), line, font=fnt, fill=(0,0,0,255), align="center")
                y_text_pos += height
                line_count += 1

        # Get size of text
        coords = ((tmp.width, 0),(0, (tmp.height//6.4)*line_count))
        
        # Draw white background for text
        white_bg = Image.new("RGBA", tmp.size, (255,255,255,0))
        image_caption_box = ImageDraw.Draw(white_bg)
        image_caption_box.rectangle(coords, fill="white", outline="white")

        # Composite text, background & base image
        text_box = Image.alpha_composite(white_bg, txt)
        out = Image.alpha_composite(tmp, text_box)
        
        return out
    

    def fry(self, emoji: str, text: str, caption: str) -> Image.Image:
        # User can skip an argument by using any of these values
        is_none = ["-", " ", "", "None", "none", None]
        
        img = self.img
        
        # Add emojis __BEFORE__ changing contrast and adding noise
        if emoji not in is_none:
            img = self.add_emojis(img, emoji)
        
        # Change contrast
        img = self.change_contrast(img, level=100)
        
        # Add noise
        img = self.add_noise(img, 1)

        # Add text
        if text not in is_none:
            img = self.add_text(img, text)
        
        # Add caption graphic
        if caption not in is_none:
            img = self.add_caption(img, caption)

        jpg_copy = img.copy().convert("RGB")

        # Create io.BytesIO file-like bytestream
        rtn_img = io.BytesIO()
        
        # Save image as shitty jpeg
        jpg_copy.save(rtn_img, format="JPEG", quality=30)
        
        # Seek to byte 0, so discord.File can .read() the file object
        rtn_img.seek(0)
        
        return rtn_img
        


