import asyncio
import itertools
import os
import random
import subprocess
import sys
import threading
import traceback
from collections import deque
from queue import Queue
from functools import partial
from pathlib import Path
from typing import Iterator, Tuple

import discord
import gtts
import youtube_dl
from async_timeout import timeout
from discord import opus
from discord.ext import commands
from youtube_dl import YoutubeDL

from cogs.base_cog import BaseCog
from ext_module import ExtModule
from utils.config import SOUND_DIR


class SoundFolder:
    """
    Class holding directory listing and markdown formatting
    of a specific folder/directory.
    """

    MAXLEN = 1800
    BASE_DIR = SOUND_DIR
    
    def __init__(self, folder:str="", header:str=None, lang: str="", color: str=None) -> None:
        self.folder = folder
        self.header = header
        self.lang = lang
        if color is not None and lang != "":
            self.color = color
        else:
            self.color = ""

    @property
    def sound_list(self) -> list:    
        return sorted([i[:-4].lower() for i in os.listdir(f"{self.BASE_DIR}/{self.folder}") if i.endswith(".mp3")])
    
    def get_msg(self) -> Iterator[str]:
        md_start = f"```{self.lang}\n"
        if self.header is not None:
            head = f"{self.header}:"
        else:
            head = ""
        msg = f"{md_start}{head}\n\n"
        for sound in self.sound_list:
            # 1 line per sound file
            _msg = f"{self.color}{sound}\n"
            if len(msg + _msg)>self.MAXLEN:
                # Append "```" and yield msg if adding line exceeds char limit
                msg += "```"
                yield msg
                # Begin new message
                msg = "```\n"
                msg += _msg
            else:
                msg += _msg
        else:
            msg += "```"
            yield msg


class SoundboardCog(BaseCog):
    """Cog for the soundboard feature"""

    def __init__(self, bot: commands.Bot, log_channel_id: int) -> None:
        super().__init__(bot, log_channel_id)
        self.is_playing = False
        self.folder = SOUND_DIR
        #self.queue = Queue()
        self.queue = deque()
        self.vc = None
        self.sub_dirs = [SoundFolder(), # Base sound dir with uncategorized sounds
                         SoundFolder("tts", "TTS", "css"), 
                         SoundFolder("ytdl", "YouTube", "fix")]
    @property
    def sound_list(self) -> list:
        """
        Returns list of files in the sound folder provided on class instantiation.
        
        Returns:
            sound_list: list of file names, all lowercase and without the .mp3 file extension.
        
        Raises Exception if the folder contains no .mp3 files.
        """

        s = list(itertools.chain(*[sf.sound_list for sf in self.sub_dirs]))
        if not s:
            raise Exception("No mp3 files in the given folder")
        return s

    async def on_ready(self) -> None:
        opus.load_opus('libopus')

    @commands.command(name='play',
                      description=' tags/name || Plays the sound with the first name found in the arguments.'
                                  ' If no name is found, plays a random sound which has all tags found in the aguments.'
                                  ' Ignores upper/lowercase.'
                                  ' If no tags are found or no sound with all the given tags exists'
                                  ' the sound is chosen randomly.'
                                  ' Requires you to be in a voice channel!')
    async def play(self, ctx: commands.Context, *args, **kwargs) -> None:
        """
        Plays sound in message author's voice channel, unless otherwise specified.

        args:
            *args: Name of sound file to play. If len(args)>1, args are joined into
            single string separated by spaces.
        """
        # Remote voice channel
        remote_vc = kwargs.pop("vc", None)
        
        if remote_vc is not None:
            voice_channel = remote_vc
        else:
            try:  # user must be connected to a voice channel
                voice_channel = ctx.author.voice.channel
            except AttributeError:
                await ctx.send('To use this command you have to be connected to a voice channel!')
                raise discord.DiscordException
        
        async def parse_sound_name(arg) -> str:
            if arg in self.sound_list:
                for sf in self.sub_dirs:
                    for sound in sf.sound_list:
                        if sound == arg:
                            if sf.folder:
                                folder = f"{sf.folder}/"
                            else:
                                folder = sf.folder # empty string
                            return folder, sound
            else:
                if len(args)>0:
                    err = f"Could not find sound with name {arg}"
                    await ctx.send(err)
                    raise Exception(err)
                else:
                    sound_name = random.choice(self.sound_list)
                    return await parse_sound_name(sound_name)
        
        arg = " ".join(args).lower()
        subdir, sound_name = await parse_sound_name(arg)
        self.queue.append((subdir, sound_name))
        
        queue_msg = f"**{sound_name}** added to queue."

        if not self.vc or not self.vc.is_playing():
            try:
                self.vc = await voice_channel.connect()
            except discord.ClientException:
                def_msg = ('I am already playing in a voice channel.'
                            ' Please try again later or stop me with the stop command!')   
                await ctx.send(queue_msg) 
            else:
                auth_vc = ctx.author.voice.channel
                # THIS IS AWFUL BUT IT WORKS. YIKES.
                while(len(self.queue)) > 0:
                    _nxt = self.queue.popleft()
                    await self.play_vc(ctx, _nxt)
                    while self.vc.is_playing():
                        # Workaround for threading issues
                        # Without this while-loop, the vc instantly disconnects.
                        await asyncio.sleep(0.25)
                else:
                    #await np_msg.delete()
                    for connection in self.bot.voice_clients:
                        if auth_vc == connection.channel:
                            await connection.disconnect()
        else:
            await ctx.send(queue_msg)
    
    async def play_vc(self, ctx, sound) -> None:
        subdir, sound_name = sound
        self.is_playing = True
        def after_playing(np_msg) -> None:
            coro = np_msg.delete()
            fut = asyncio.run_coroutine_threadsafe(coro, self.bot.loop)
            self.is_playing = False     
        
        try:
            self.vc.play(discord.FFmpegPCMAudio(f"{self.folder}/{subdir}{sound_name}.mp3"),
                                after=lambda e: after_playing(np_msg))
        except:
            pass
        else:
            np_msg = await ctx.send(f"```css\nPlaying: {sound_name}\n```")
        await self.send_log('Playing: ' + sound_name)

    @commands.command(name="progress")
    async def progress(self, ctx: commands.Command) -> None:
        for k in dir(self.vc._player):
            attr = getattr(self.vc._player, k)
            print(k, attr, sep=": ")

    
    @commands.command(name="rplay")
    async def remoteplay(self, ctx: commands.Context, channel_id: int, *args):
        """
        Command for playing sound in a given voice channel `channel_id` without 
        requiring the user invoking the command to be connected to said channel.
        """
        help_str = "Usage: `!rplay <channel_id> <sound name>`"
        
        vc = discord.utils.get(self.bot.get_all_channels(), id=channel_id)
        if vc is None:
            err = f"Could not find voice channel with id {channel_id}.\n{help_str}"
            await ctx.send(err)
            raise Exception(err)
        cmd = self.bot.get_command("play")
        await ctx.invoke(cmd, *args, vc=vc)

    @commands.command(name='stop',
                      aliases=['halt'],
                      description='The bot will stop playing a sound and leave the current voice channel.'
                                  'Requires you to be in the same voice channel as the bot!')
    async def stop(self, ctx: commands.Context) -> None:
        """This function stops the bot playing a sound and makes it leave the current voice channel.
         Args:
             ctx: The context of the command, which is mandatory in rewrite (commands.Context)
             """
        async def stop_playing() -> None:
            for connection in self.bot.voice_clients:
                if ctx.author.voice.channel == connection.channel:
                    await connection.disconnect()
            else:
                self.is_playing = False
                self.queue.clear()
                self.vc = None

        if len(self.queue) > 0:
            def pred(m) -> bool:
                return m.author == ctx.message.author and m.channel == ctx.message.channel
            msg = ("Are you sure you want to stop sounds and clear the queue?\n"
                   "Reply **Y** to stop and clear queue, **S** to skip this sound only, or **N** to abort")
            await ctx.send(msg)
            try:
                reply = await self.bot.wait_for("message", check=pred, timeout=10.0)
            except asyncio.TimeoutError:
                await ctx.send("No reply from user. Aborting.")
            else:
                r = reply.content.lower()
                if r in ["s", "skip"]:
                    skip_cmd = self.bot.get_command("skip")
                    await ctx.invoke(skip_cmd)
                    await ctx.send("Skipping. Use the `!skip` command next time.")
                elif r in ["y", "yes", "stop"]:
                    await stop_playing()
                else:
                    await ctx.send("Doing nothing.")
        else:
            await stop_playing()
    @commands.command(name='skip',
                      aliases=["next"])
    async def skip(self, ctx: commands.Context) -> None:
        self.is_playing = False
        self.vc.stop()
        if len(self.queue) > 0:
            await self.play_next(ctx)   

    async def play_next(self, ctx: commands.Context) -> None:
        play_cmd = self.bot.get_command("play")
        next_sound = self.queue.popleft()
        if next_sound is not None:
            await self.play_vc(ctx, next_sound)
            #await ctx.invoke(play_cmd, next_sound)

    @commands.command(name='soundlist',
                      aliases=['sounds'], description='Prints a list of all sounds on the soundboard.')
    async def soundlist(self, ctx: commands.Context, filter_: str=None) -> None:
        """This function prints a list of all the sounds on the Soundboard to the channel/user where it was requested.
        Args:
            ctx: The context of the command, which is mandatory in rewrite (commands.Context)
            """
        flt = None
        if filter_ is not None:
            if filter_ in ["yt", "youtube", "ytdl"]:
                flt = "ytdl"
            elif filter_ in ["tts", "texttospeech"]:
                flt = "tts"
        if flt is None:
            flt = ""

        for sf in self.sub_dirs:
            if sf.folder == flt or filter_ is None:
                for msg in sf.get_msg():
                    await ctx.send(msg)
                if filter_ is not None:
                    break

    ### UNUSED ###
    def disconnector(self, voice_client: discord.VoiceClient, ctx: commands.Context) -> None:
        """This function is passed as the after parameter of FFmpegPCMAudio() as it does not take coroutines.
        Args:
            voice_client: The voice client that will be disconnected (discord.VoiceClient)
            """
        self.is_playing = False

        coro = voice_client.disconnect()
        fut = asyncio.run_coroutine_threadsafe(coro, self.bot.loop)
        try:
            fut.result()
        except asyncio.CancelledError:
            pass
        
        if len(self.queue) > 0:   
            next_sound = self.queue[0]
            try:
                play_cmd = self.bot.get_command("play")
                self.bot.loop.run_until_complete(ctx.invoke(play_cmd, next_sound))
            except discord.DiscordException:
                pass
            finally:
                self.queue.popleft()
    
    @commands.command(name="queue")
    async def display_queue(self, ctx:commands.Context):
        if len(self.queue)>0:
            _queue = await self.format_output([s for _, s in self.queue], enum=True, formatting="glsl")
            msg = f"Sound files currently queued up:\n{_queue}"
        else:
            msg = "No sound files in queue."
        await ctx.send(msg)
    
    @commands.command(name="texttospeech",
                      aliases=["tts", "text-to-speech"])
    async def texttospeech(self, ctx: commands.Context, text: str, language: str="en", pitch: int=0) -> None:
        
        help_str = ("3 arguments required: "
                                "`text` "
                                "`language` "
                                "`sound_name`."
                                "\nType `!tts lang` for more information about available languages.")
        
        # gTTS exception handling. 
        # The language list keeps breaking between versions.
        try:
            valid_langs = gtts.lang.tts_langs()
        except:
            await ctx.send("Google Text-to-Speech needs to be updated. Try again later.")
            await self.send_log(f"**URGENT**: Update gTTS. <pip install -U gTTS> {self.author_mention}")
            raise Exception
        # User error and help arguments
        if text is None:
            await ctx.send("Text for TTS must be specified.")
            raise Exception 
        elif text in ["languages", "lang", "options"]:
            output = '```Available languages:\n\n'
            for language_long, language_short in valid_langs.items():
                output += f"{language_long}: {language_short}\n"
            output += "```"
            await ctx.send(output)
            raise Exception

        if language in valid_langs.keys():
            tts = gtts.gTTS(text=text, lang=language)
            sound_name = text.split(" ")[0]

            # I'll implement pitch shit later sorry
            if True:
                file_prefix = ""
            else:  
                if pitch != 0:
                    file_prefix = "_"
                else:
                    file_prefix = ""
            
            # Generate file name and relative file path
            _num = 0
            file_suffix = lambda x: "" if x == 0 else x
            file_path = lambda n: f"sounds/{file_prefix}{sound_name}{file_suffix(n)}.mp3"
            
            # Check if a file with identical name already exists
            while Path(file_path(_num)).exists():
                _num += 1
            else:
                tts.save(file_path(_num))
                sound_name = f"{sound_name}{file_suffix(_num)}"
                await ctx.send(f'Sound created: **{sound_name}**')
        else:
            await ctx.send(f'"{language}" is not a valid TTS language option.')
            raise Exception

        # Try to play created sound file in author's voice channel afterwards
        try:
            if ctx.message.author.voice.channel is not None:
                cmd  = self.bot.get_command('play')
                await ctx.invoke(cmd, sound_name)
        except AttributeError:
            pass

    @commands.command(name="ytdl")
    async def download_track(self, ctx: commands.Context, url: str) -> None:
        
        ytdl_opts = {
            'outtmpl': 'sounds/ytdl/%(title)s.%(ext)s',
            "verbose": True
                }
        if "youtube" in url:
            # This is a YouTube-specific setting
            ytdl_opts["format"] = "bestaudio"
        dl_msg = await ctx.send("```cs\n# Downloading video...\n```")
        with youtube_dl.YoutubeDL(ytdl_opts) as ydl:
            result = ydl.extract_info(url=url, download=True, extra_info=ytdl_opts)
            res = ydl.prepare_filename(result)
            directory, file_name = os.path.split(res)
            _file, ext = os.path.splitext(file_name)
        
        original = f"{directory}/{file_name}"
        _file = " ".join(filter(None, _file.split(" "))) # Prevent trailing space(s)
        new = f"{directory}/{_file}.mp3"
        cmd = f'ffmpeg -n -i "{original}" -acodec libmp3lame -ab 128k "{new}"'
        
        def convert():   
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).wait()
        
        await dl_msg.delete()
        msg = await ctx.send(f"```fix\nConverting {_file} to mp3.\n```")
        await self.bot.loop.run_in_executor(None, convert)
        os.remove(original)
        await msg.delete()
        
        try:
            if ctx.message.author.voice.channel is not None:
                cmd  = self.bot.get_command('play')
                await ctx.invoke(cmd, _file)
        except AttributeError:
            pass
