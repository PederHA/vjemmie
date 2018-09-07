"""
Some frying methods in this module are based on https://github.com/asdvek/DeepFryBot,
but modified to fit into a class structure, rather than being standalone functions.

Original methods such as `add_text()` and `add_caption()` are added to provide
a richer set of functionality than what DeepFryBot provides. 
"""

from PIL import Image, ImageDraw, ImageFont
import numpy as np
import cv2
from random import randint
import requests
import shutil
from os import listdir
from typing import Iterable


class ImageFryer:
    def __init__(self, img_url):
        self.img_url = img_url
        self.img_path = self.download_img(self.img_url)
        self.img = self.get_img(self.img_path)

    def download_img(self, url: str) -> None:
        r = requests.get(url, stream=True)
        file_type = url.rsplit(".")[-1].lower()
        img_file_types = ["jpg", "jpeg", "png", "gif"]
        if file_type in img_file_types:
            path = f"temp/image_to_fry.{file_type}"
            with open(path, 'wb+') as f:
                r.raw.decode_content = True
                shutil.copyfileobj(r.raw, f)
        return path

    def get_img(self, path: str) -> Image.Image:
        img =  Image.open(path)
        return img
    
    @staticmethod
    def get_files_in_dir(item_category: str) -> str:
        """
        This method was repurposed to work with an "all" filter, which lists
        both emojis and captions. To make this happen using the existing
        functionality of the method, a sort of hacky band-aid fix was put
        in place. It looks ugly, but it works for now.

        At the moment, this method suffers from god-awful variable names, 
        which might make its logic confusing at first glance.
        """

        item_categories = ["emojis", "captions", "all"]
        if item_category in item_categories:
            items = []
            output_buffer = ""
            
            if item_category == "all":
                # Take first 2 indices of `item_categories`
                items = item_categories[:2]
            else:
                # Make a 1 index long list, so it doesn't break the for-loop below
                items.append(item_category)

            # Is only iterated through once if not called with the "all" argument  
            for item_type in items:
                item_list = []
                for item in listdir(f"deepfryer/images/{item_type}"):
                    item, _ = item.split(".")
                    item_list.append(item)
                if item_category != "all":
                    return ImageFryer.format_output(item_list, item_type)
                else:
                    output_buffer += ImageFryer.format_output(item_list, item_type)
            # Is only reached if for-loop finishes iteration without hitting the return statement above
            else:
                return output_buffer
                    
    
    @staticmethod
    def format_output(list_of_items: Iterable, item_type: str) -> str:
        """
        Formats an iterable, and creates a markdown multi-line code block
        in which every item in the iterable is placed on separate lines.

        Returns a string containing said multi-line code block.
        """
        output = "```"
        output += f"Available {item_type}:\n\n"
        for item in list_of_items:
            output += f"{item}\n"
        else:
            output += "```"
        return output

    def change_contrast(self, img: Image.Image, level:int=115) -> Image.Image:
        factor = (259 * (level + 255)) / (255 * (259 - level))
        def contrast(c):
            return 128 + factor * (c - 128)
        return img.point(contrast)

    def add_noise(self, img: Image.Image, factor:int=1) -> Image.Image:
        def noise(c):
            return c*(1+np.random.random(1)[0]*factor-factor/2)
        return img.point(noise)
    
    def add_emojis(self, img: Image.Image, emoji_name:str, max: int):
        # create a temporary copy if img
        tmp = img.copy()
        default_emoji = 'smilelaugh'
        try:
            emoji = Image.open(f'deepfryer/images/emojis/{emoji_name.lower()}.png')
        except:
            emoji = Image.open(f"deepfryer/images/emojis/{default_emoji}.png")
        for i in range(1, randint(max-2,max)):
            # add laughing emoji to random coordinates
            coord = np.random.random(2)*np.array([img.width, img.height])
            resized = emoji.copy()
            size = int((img.width/10)*(np.random.random(1)[0]+1))
            resized.thumbnail((size, size), Image.ANTIALIAS)
            tmp.paste(resized, (int(coord[0]), int(coord[1])), resized)
        return tmp

    def add_caption(self, img, caption_name):
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
        A bit hacky in its implementation, but works alright for now.
        """
        tmp = img.copy()        
        tmp = tmp.convert("RGBA")

        txt = Image.new("RGBA", tmp.size, (255,255,255,0))
        fnt = ImageFont.truetype(".deepfryer/fonts/arial.ttf", 50)
        d = ImageDraw.Draw(txt)
        d.text((10,60), text_string, font=fnt, fill=(0,0,0,255))
        
        white_bg = Image.new("RGBA", tmp.size, (255,255,255,0))
        image_caption_box = ImageDraw.Draw(white_bg)
        coords = ((tmp.width, 0),(0, tmp.height//6.4))
        image_caption_box.rectangle(coords, fill="white", outline="white")

        text_box = Image.alpha_composite(white_bg, txt)
        out = Image.alpha_composite(tmp, text_box)
        return out

    def fry(self, emoji, text, caption) -> None:
        # TODO: Each method should modify the instance variable `self.img`, 
        # rather than returning a new `Image.Image` object each time
        interpret_as_none = ["-", " ", "", "None", "none"]
        img = self.img
        if emoji not in interpret_as_none:
            img = self.add_emojis(img, emoji, 5)
        if caption not in interpret_as_none:
            img = self.add_caption(img, caption)
        img = self.change_contrast(img, 100)
        img = self.add_noise(img, 1)
        if text not in interpret_as_none:
            img = self.add_text(img, text)

        jpg_copy = img.copy().convert("RGB")
        # For now, the image is just saved to disk, and not returned
        # as a file-like object to the !deepfry method.
        jpg_copy.save("deepfryer/temp/fried_img.jpg", "JPEG")


