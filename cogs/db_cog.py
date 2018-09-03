"""
Not technically cog, but who's gonna fucking arrest me, huh?
"""

import sqlite3
import os
import datetime
import time
import random
from collections import namedtuple
from typing import Tuple
import copy
import discord
from utils.ext_utils import is_int
from discord.ext import commands


class DatabaseHandler:

    def __init__(self, db_path):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
        self.c = self.conn.cursor()
    

    async def get_memes(self, topic: str, ctx: commands.Context, args: tuple):
        meme_index = None
        print_list = False
        print_all_memes = False

        if topic == "list_memes":
            topic_query = ""
            topic_col = "topic, "
            print_all_memes = True
        else:
            topic_col = ""
            topic_query = f'WHERE topic == "{topic}" ' 
        # DB columns: topic, title, description, content, media_type 
        self.c.execute(f'SELECT {topic_col}title, description, content, media_type FROM pfm_memes {topic_query}')
        
        # Users can request specific images by adding an integer as argument to a meme command
        # Example: `!nezgroul 5` will always post the same, specific image

        if len(args) > 0:
            if is_int(args[0]):
                try:
                    meme_index = (int(args[0]) - 1)
                    if 0 > meme_index:
                        meme_index = 0
                except:
                    meme_index = None
            elif args[0] == "list":
                print_list = True
        
        # Returns list of tuples. Each tuple represents a database row.
        memes = self.c.fetchall()
        
        if not print_list:
            # If args contains an integer, try to select specific meme
            if meme_index is not None:
                try:
                    meme = memes[meme_index]
                except:
                    await ctx.send("Meme index out of range! Random meme selected instead.")
                    meme = random.choice(memes)
            else:
                # Choose 1 random meme
                meme = random.choice(memes)

            # Determine message formatting based on content type (image, video, url, etc.)
            content, embed = await self.format_meme(meme, ctx)

            # Send message with generated content and embed objects
            await ctx.send(content=content, embed=embed)
        
        else:
            output = "```"
            meme_topic = ""
            n = 1
            for meme in memes:
                if print_all_memes:
                    topic, title, description, content, media_type = meme
                else:
                    title, description, content, media_type = meme
                if meme_topic != topic:
                    output += f"\n!{topic}\n-----\n"
                    meme_topic = topic
                    n = 1
                output += f"{n}: {title}\n"
                n += 1
            else:
                output += "```"
            await ctx.send(output)

    async def format_meme(self, meme, ctx):
        embed = discord.Embed()
        title, description, content, media_type = meme
        
        if media_type == "url" or media_type == "mp4":
            return content, None
        elif media_type == "txt":
            # SQLite causes newline to be escaped. Replace with proper newline.
            content = content.replace("\\n", "\n")
            return content, None
        elif media_type == "img":
            embed.set_image(url=content)
            return None, embed

    ###################################################
    # Some DB methods leftover from a different project
    ###################################################

    def get_unix_and_datestamp(self) -> tuple:
        unix = time.time()
        datestamp = str(datetime.datetime.fromtimestamp(unix).strftime("%Y-%m-%d %H:%M:%S"))
        return unix, datestamp
    
    def bool_to_int(self, bool_var: bool) -> int:
        """
        SQLite has no bool type, so True and False
        are represented in the DB by the values 1 and 0.
        """
        if bool_var:
            int_var = 1
        else:
            int_var = 0
        return int_var

    def close_db(self) -> None:
        self.c.close()
        self.conn.close()
