"""
Not technically cog, but who's gonna fucking arrest me, huh?
"""

import copy
import datetime
import os
import random
import sqlite3
import time
import traceback
from collections import namedtuple
from typing import Tuple

import discord
from discord.ext import commands

from utils.ext_utils import is_int
import trueskill

class DatabaseHandler:

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
        self.c = self.conn.cursor()
    

    async def get_memes(self, topic: str, ctx: commands.Context, args: tuple) -> None:
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

    async def format_meme(self, meme, ctx) -> tuple:
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
    
    async def whosaidit(self, message: discord.Message) -> None:
        """
        Tracking begun 19/09/2018
        """
        update_row = False
        msg_author = message.author.name    
        for name, occurences in self.c.execute(f'SELECT "NAME", "occurences" FROM "wordtrack"'):
            if name == msg_author:
                update_row = True
                break
        else:
            # Create new entry in DB if message author's name does not exist already
            self.c.execute(f'INSERT INTO `wordtrack`(`name`,`occurences`) VALUES ("{msg_author}",1);')
        if update_row:
            try:
                occurences = int(occurences)
                occurences += 1
            except:
                pass
            else:
                self.c.execute(f'UPDATE `wordtrack` SET `occurences`={occurences} WHERE "name"="{name}";')
        self.conn.commit()

    # Rating
    def add_user(self, user: discord.Member, realname: str, game: str, base_rating: float) -> str:
        base_rating = float(base_rating)
        if realname is not None:
            realname = realname.lower()
        else:
            realname=user.name.lower()
        username = user.name.lower()
        
        try:
            self.c.execute(f'INSERT INTO `{game}`(`name`,`alias`,`id`,`rating`, `wins`, `losses`) VALUES (?, ? ,? ,?, ?, ?)', 
                          (realname, username, user.id, base_rating, 0, 0))
        except sqlite3.IntegrityError:
            msg = "User with that name or ID already exists in the database!"
        except:
            exc = traceback.format_exc()
            print(exc)
            msg = "Unknown error occured!"
        else: 
            self.conn.commit()
            msg = f"Added {user.name} to DB!"
        finally:
            return msg
    
    def get_players(self, game: str, alias: bool=False) -> list:
        Player = namedtuple("player", "name rating wins losses")
        players = []
        if alias:
            _name = "alias"
        else:
            _name = "name"
        for name, _alias, rating, wins, losses in self.c.execute(f'SELECT "name", "alias", "rating", "wins", "losses" from {game}'):
            if alias and _alias is not None:
                nick = _alias
            if not alias or _alias is None:
                nick = name       
            players.append(Player(nick, rating, wins, losses))
        # Sort players by rating from high to low.
        players = sorted(players, key=lambda x: x[1], reverse=True)
        return players

    def update_rating(self, player: str, rating: trueskill.Rating, win: bool=True, game: str="legiontd") -> None:
        if win:
            result = "wins"
        else:
            result = "losses"
        self.c.execute(f"""SELECT "{result}" FROM {game} WHERE name == "{player}" """)
        result_n = self.c.fetchone()
        result_n = result_n[0] + 1
        self.c.execute(f"""UPDATE {game} SET rating = {rating.mu}, {result} = {result_n}, last_played = {time.time()}  WHERE name == "{player}" """)
        self.conn.commit()

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
