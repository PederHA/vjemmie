"""
Some frying methods in this module are based on https://github.com/asdvek/DeepFryBot,
but modified to fit into a class structure, rather than being standalone functions.

Original methods such as `add_text()` and `add_caption()` are added to provide
a richer set of functionality than what DeepFryBot provides.

# TODO: Make methods async
#       Remove image_url from __init__. Should be passed into `fry()` instead.
"""

from PIL import Image, ImageDraw, ImageFont
import numpy as np
import cv2
from random import randint
import requests
import shutil
from os import listdir
from typing import Iterable
import textwrap
from utils.exceptions import WordExceededLimit, NonImgURL, InvalidURL
import math
import progressbar

class ImageFryer:
    def __init__(self, img_url):
        self.img_url = img_url
        self.img_path = self.download_img(self.img_url)
        self.img = self.get_img(self.img_path)

    def download_img(self, url: str) -> None:
        r = requests.get(url, stream=True)
        try:
            file_type = url.rsplit(".")[-1].lower()
        except:
            raise InvalidURL
        img_file_types = ["jpg", "jpeg", "png", "gif"]
        if file_type in img_file_types:
            path = f"temp/image_to_fry.{file_type}"
            with open(path, 'wb+') as f:
                r.raw.decode_content = True
                shutil.copyfileobj(r.raw, f)
            return path
        else:
            raise NonImgURL
        

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
        default_emoji = 'b'
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

        tmp = img.copy()        
        tmp = tmp.convert("RGBA")

        txt = Image.new("RGBA", tmp.size, (255,255,255,0))
        fnt = ImageFont.truetype(".deepfryer/fonts/LiberationSans-Regular.ttf", tmp.height//8)         
        d = ImageDraw.Draw(txt)
        
        # Each character is aproximately 26 pixels
        try:
            lines = textwrap.wrap(text_string, width=(tmp.width//26.5))
        except:
            raise WordExceededLimit
        # Line count is used to determine height of text background
        # as well as limiting the amount of text that is displayed
        line_count = 0
        y_text = 0
        for  line in lines:
            if line_count < 2:
                width, height = fnt.getsize(line)
                d.text((0,y_text), line, font=fnt, fill=(0,0,0,255), align="center")
                y_text += height
                line_count += 1
            
        white_bg = Image.new("RGBA", tmp.size, (255,255,255,0))
        image_caption_box = ImageDraw.Draw(white_bg)
        coords = ((tmp.width, 0),(0, (tmp.height//6.4)*line_count))
        image_caption_box.rectangle(coords, fill="white", outline="white")

        text_box = Image.alpha_composite(white_bg, txt)
        out = Image.alpha_composite(tmp, text_box)
        return out
    
    def bulge(self, img, f, r, a, h, ior):
        """
        Pretty much just copy-pasted from DeepFryBot.
        
        This implementation of image bulging is _very_ slow, and as a result
        it is currently disabled.
        """
        # return the length of vector v
        def length(v):
            return np.sqrt(np.sum(np.square(v)))


        # returns the unit vector in the direction of v
        def normalise(v):
            return v/length(v)

        # print("Creating a bulge at ({0}, {1}) with radius {2}... ".format(f[0], f[1], r))

        # load image to numpy array
        width = img.width
        height = img.height
        img_data = np.array(img)

        # ignore too large images
        if width*height > 3000*3000:
            return img

        # determine range of pixels to be checked (square enclosing bulge), max exclusive
        x_min = int(f[0] - r)
        if x_min < 0:
            x_min = 0
        x_max = int(f[0] + r)
        if x_max > width:
            x_max = width
        y_min = int(f[1] - r)
        if y_min < 0:
            y_min = 0
        y_max = int(f[1] + r)
        if y_max > height:
            y_max = height

        # make sure that bounds are int and not np array
        if isinstance(x_min, type(np.array([]))):
            x_min = x_min[0]
        if isinstance(x_max, type(np.array([]))):
            x_max = x_max[0]
        if isinstance(y_min, type(np.array([]))):
            y_min = y_min[0]
        if isinstance(y_max, type(np.array([]))):
            y_max = y_max[0]

        # array for holding bulged image
        bulged = np.copy(img_data)
        for y in (range(y_min, y_max)):
            for x in range(x_min, x_max):
                ray = np.array([x, y])

                # find the magnitude of displacement in the xy plane between the ray and focus
                s = length(ray - f)

                # if the ray is in the centre of the bulge or beyond the radius it doesn't need to be modified
                if 0 < s < r:
                    # slope of the bulge relative to xy plane at (x, y) of the ray
                    m = -s/(a*math.sqrt(r**2-s**2))

                    # find the angle between the ray and the normal of the bulge
                    theta = np.pi/2 + np.arctan(1/m)

                    # find the magnitude of the angle between xy plane and refracted ray using snell's law
                    # s >= 0 -> m <= 0 -> arctan(-1/m) > 0, but ray is below xy plane so we want a negative angle
                    # arctan(-1/m) is therefore negated
                    phi = np.abs(np.arctan(1/m) - np.arcsin(np.sin(theta)/ior))

                    # find length the ray travels in xy plane before hitting z=0
                    k = (h+(math.sqrt(r**2-s**2)/a))/np.sin(phi)

                    # find intersection point
                    intersect = ray + normalise(f-ray)*k

                    # assign pixel with ray's coordinates the colour of pixel at intersection
                    if 0 < intersect[0] < width-1 and 0 < intersect[1] < height-1:
                        bulged[y][x] = img_data[int(intersect[1])][int(intersect[0])]
                    else:
                        bulged[y][x] = [0, 0, 0]
                else:
                    bulged[y][x] = img_data[y][x]
        img = Image.fromarray(bulged)
        return img
    
    def fry(self, emoji: str, text: str, caption: str) -> None:
        # (Maybe?) TODO: Each method should modify the instance variable `self.img`, 
        # rather than returning a new `Image.Image` object each time
        bulge_enabled = False
        interpret_as_none = ["-", " ", "", "None", "none"]
        img = self.img
        if emoji not in interpret_as_none:
            img = self.add_emojis(img, emoji, 5)

        img = self.change_contrast(img, 100)
        img = self.add_noise(img, 1)
        if bulge_enabled:
            [w, h] = [img.width - 1, img.height - 1]
            w *= np.random.random(1)
            h *= np.random.random(1)
            r = int(((img.width + img.height) / 10) * (np.random.random(1)[0] + 1))
            img = self.bulge(img, np.array([int(w), int(h)]), r, 3, 5, 1.8)
        if text not in interpret_as_none:
            img = self.add_text(img, text)
        if caption not in interpret_as_none:
            img = self.add_caption(img, caption)    

        jpg_copy = img.copy().convert("RGB")
        # For now, the image is just saved to disk, and not returned
        # as a file-like object to the !deepfry method.
        jpg_copy.save("deepfryer/temp/fried_img.jpg", "JPEG")


