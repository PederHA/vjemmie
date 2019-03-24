import asyncio
import itertools
import os
import random
import subprocess
import sys
import threading
import traceback
import wave
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
    
    def __init__(self, folder:str="", header:str=None, color: str=None) -> None:
        self.folder = folder
        self.header = header if header else "General"
        self.color = color

    @property
    def sound_list(self) -> list:    
        return sorted([i[:-4] for i in os.listdir(f"{self.BASE_DIR}/{self.folder}") if i.endswith(".mp3")])

class SoundCog(BaseCog):
    """Cog for the soundboard feature"""
    VALID_FILE_TYPES = ["mp3"]
    def __init__(self, bot: commands.Bot, log_channel_id: int) -> None:
        self.is_playing = False
        self.folder = SOUND_DIR
        #self.queue = Queue()
        self.queue = deque()
        self.vc = None
        self.sub_dirs = [SoundFolder(color="blurple"), # Base sound dir with uncategorized sounds
                         SoundFolder("tts", "TTS", "red"), 
                         SoundFolder("ytdl", "YouTube", "blue")]
        super().__init__(bot, log_channel_id)
    
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
                raise discord.DiscordException('To use this command you have to be connected to a voice channel!')
        
        async def parse_sound_name(arg) -> str:
            #if arg in self.sound_list:
            for sf in self.sub_dirs:
                for sound_filename in sf.sound_list:
                    if sound_filename.lower() == arg:
                        if sf.folder:
                            folder = f"{sf.folder}/"
                        else:
                            folder = sf.folder # empty string
                        return folder, sound_filename
            else:
                if len(args)>0:
                    raise discord.DiscordException(f"Could not find sound with name {arg}")
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
                # THIS IS AWFUL BUT IT WORKS. YIKES.
                while(len(self.queue)) > 0:
                    _nxt = self.queue.popleft()
                    await self.play_vc(ctx, _nxt)
                    if self.vc is not None:
                        while self.vc and self.vc.is_playing():
                            # Workaround for threading issues
                            # Without this while-loop, the vc instantly disconnects.
                            await asyncio.sleep(0.25)
                else:
                    #await np_msg.delete()
                    for connection in self.bot.voice_clients:
                        if voice_channel == connection.channel:
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
            filepath = f'{self.folder}/{subdir}{sound_name}.mp3'
            self.vc.play(discord.FFmpegPCMAudio(filepath),
                                after=lambda e: after_playing(np_msg))
        except:
            pass
        else:
            np_msg = await ctx.send(f"```css\nPlaying: {sound_name}\n```")
        await self.send_log('Playing: ' + sound_name)

    @commands.command(name="rplay")
    async def remoteplay(self, ctx: commands.Context, channel: commands.VoiceChannelConverter, *sound_name):
        """
        Command for playing sound in a given voice channel `channel_id` without 
        requiring the user invoking the command to be connected to said channel.
        """
        help_str = "Usage: `!rplay <channel_id> <sound name>`"
        cmd = self.bot.get_command("play")
        await ctx.invoke(cmd, *sound_name, vc=channel)

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
    
    async def do_send(self, ctx, header: str, content: str, footer: bool, color: str=None) -> None:
        if not header:
            header = "general"
        embed = await self.get_embed(ctx, fields=[self.EmbedField(header, content)], footer=footer, color=color)
        await ctx.send(embed=embed)
    
    @commands.command(name="soundlist",
                      aliases=["sounds"], description='Prints a list of all sounds on the soundboard.')
    async def soundlist(self, ctx: commands.Context, category: str=None) -> None:
        """This function prints a list of all the sounds on the Soundboard to the channel/user where it was requested.
        Args:
            ctx: The context of the command, which is mandatory in rewrite (commands.Context)
            """
        
        def get_category(category: str) -> str:
            if category is not None:
                if category in ["yt", "youtube", "ytdl"]:
                    return "ytdl"
                elif category in ["tts", "texttospeech"]:
                    return "tts"
                # Add this and raise exception if category is not recognized? 
                # elif category in ["general", "uncategorized"]:
                #     return ""
                # else:
                #     return None   
            return ""
        
        # Parse argument `category`
        if not category:
            _categories = [sf.header for sf in self.sub_dirs]
            categories = ", ".join(_categories)
            raise discord.DiscordException(f"Cannot display all sounds at once. Specify a category from: {categories}")
        else:     
            category = get_category(category)

        for sf in self.sub_dirs:
            if sf.folder == category or not category:
                _out = ""
                for sound in sf.sound_list:
                    fmt_sound = f"\n{sound}"
                    if len(_out + fmt_sound) < 1000:
                        _out += fmt_sound
                    else:
                        await self.do_send(ctx, sf.header, _out, footer=False, color=sf.color)
                        _out = ""
                else:
                    if _out:
                        await self.do_send(ctx, sf.header, _out, footer=True, color=sf.color)

    @commands.command(name="search")
    async def search_sound(self, ctx: commands.Context, *search_query: str) -> None:
        _out = ""
        search_query = " ".join(search_query)
        for sf in self.sub_dirs:
            for sound in sf.sound_list:
                if search_query.lower() in sound.lower():
                    fmt_sound = f"\n{sound}"
                    if len(_out + fmt_sound) < 1000:
                        _out += fmt_sound
                    else:
                        await self.do_send(ctx, sf.header, _out, footer=False)
                        _out = ""
            else:
                if _out:
                    await self.do_send(ctx, sf.header, _out, footer=True)
        if not _out:
            await ctx.send("No results")


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
        
        help_str = ("2 arguments required: "
                                "`text` "
                                "`language` "
                                "\nType `!tts lang` for more information about available languages.")
        
        # gTTS exception handling. 
        # The language list keeps breaking between versions.
        try:
            valid_langs = gtts.lang.tts_langs()
        except:
            await self.send_log(f"**URGENT**: Update gTTS. <pip install -U gTTS> {self.AUTHOR_MENTION}")
            raise discord.DiscordException("Google Text-to-Speech needs to be updated. Try again later.")
        
        # User error and help arguments
        if text is None:
            raise discord.DiscordException("Text for TTS is a required argument.") 
        
        elif text in ["languages", "lang", "options"]:
            langs = [f"{lang_long}: {lang_short}" for lang_long, lang_short in valid_langs.items()]
            output = await self.format_output(langs, item_type="languages") # should be item_name/category smh
            await ctx.send(output)
        
        elif language in valid_langs.keys() and text is not None:
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
            
            # Try to play created sound file in author's voice channel afterwards
            try:
                if ctx.message.author.voice.channel is not None:
                    cmd  = self.bot.get_command('play')
                    await ctx.invoke(cmd, sound_name)
            except AttributeError:
                pass

    @commands.command(name="ytdl")
    async def download_track(self, ctx: commands.Context, url: str) -> None:    
        """Downloads an online video and converts it to an .mp3 file
        
        Parameters
        ----------
        ctx : commands.Context
            Discord Context object
        url : str
            HTTP(s) URL of video
        """

        ytdl_opts = {
            'outtmpl': 'sounds/ytdl/%(title)s.%(ext)s',
            "verbose": True
                }
        if "youtube" in url:     
            ytdl_opts["format"] = "bestaudio"   # this is a YouTube-specific setting
        
        # Attempt to download video
        try:
            dl_msg = await ctx.send("```cs\n# Downloading video...\n```")
            with youtube_dl.YoutubeDL(ytdl_opts) as ydl:
                result = ydl.extract_info(url=url, download=True, extra_info=ytdl_opts)
                res = ydl.prepare_filename(result)
                directory, file_name = os.path.split(res)
                _file, ext = os.path.splitext(file_name)
        except:
            # Kind of ugly, but we need to delete message _before_ raising exception
            await dl_msg.delete()
            raise
        else:
            await dl_msg.delete()
        
        # Generate file name and ffmpeg command
        original = f"{directory}/{file_name}"
        _file = " ".join(filter(None, _file.split(" ")))    # Prevent trailing space(s)
        new = f"{directory}/{_file}.mp3"
        cmd = f'ffmpeg -n -i "{original}" -acodec libmp3lame -ab 128k "{new}"'
        #cmd = f'ffmpeg -i "{original}" -acodec libmp3lame -ab 128k "{new}"'
        #cmd = f'ffmpeg -i "{original}" -f mp3 -ab 192000 -vn "{new}"'

        def convert():   
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).wait()
        
        # Convert file to .mp3
        msg = await ctx.send(f"```fix\nConverting {_file} to mp3.\n```")
        await self.bot.loop.run_in_executor(None, convert) # Non-blocking FFMPEG conversion (i think?)
        os.remove(original)
        await msg.delete()
        
        # Play downloaded sound file in message author's channel afterwards
        try:
            if ctx.message.author.voice.channel is not None:
                cmd  = self.bot.get_command('play')
                await ctx.invoke(cmd, _file)
        except AttributeError:
            pass

    @commands.command(name="add_sound")
    async def add_sound(self, ctx: commands.Context, url: str=None) -> None:
        """Downloads a sound file supplied as a Discord message attachment
        or as an HTTP(s) URL.
        
        Parameters
        ----------
        ctx : commands.Context
            Discord Context object
        url : str, optional
            HTTP(s) URL of file. 
            If message has no attachment, command will raise
            exception if URL is None.
        
        Raises
        ------
        discord.DiscordException
            [description]
        """
        # Raise exception if message has no attachment and no URL was passed in
        if not ctx.message.attachments and not url:
            raise discord.DiscordException("A file attachment or file URL is required!")

        # Use attachment URL if possible
        if ctx.message.attachments:
            attachment = ctx.message.attachments[0]
            url = attachment.url

        # Download and save sound file
        directory, file_name, extension, sound_file = await self._do_download_sound(url)
        with open(f"{directory}/{file_name}.{extension}", "wb") as f:
            f.write(sound_file)
        await ctx.send(f"Saved file {file_name}.{extension}")    

    async def _do_download_sound(self, url: str) -> Tuple[str, str, str, bytes]:
        """Attempts to download file from URL. 
        Fails if the filetype is not .mp3.

        NOTE
        ----
        Although the code is written to accomodate additional 
        file types, only .mp3 files are supported as of yet.
        
        Parameters
        ----------
        url : `str`
            HTTP(s) URL of target file
        
        Raises
        ------
        `discord.DiscordException`
            Raised if URL can not be parsed. Ideally this should be
            raised if the URL is not a direct link to a file.
        `discord.DiscordException`
            Raised if file type of downloaded file is not found in
            dict: VALID_FILETYPES
        
        Returns
        -------
        `Tuple[str, str, str, bytes]`
            Tuple consisting of:
                str: Target directory name
                str: Sound file name
                str: File extension
                bytes: Downloaded sound file.
                (See BaseCog.download_from_url() for further
                documentation of downloaded bytes object)
        """
        VALID_FILETYPES = {
                # Will expand
                "mp3": "sounds"
            }
        # Generate formatted string of valid file types
        file_types = ", ".join(VALID_FILETYPES.keys())
        
        # Get file extension
        try:
            # TODO: This sucks. Find a cleaner way
            _, file_name, extension = url.rsplit(".", 2)
            file_name = file_name.rsplit("/", 1)[1]
        except:
            # Fails if URL is not a direct link to a file
            raise discord.DiscordException("Invalid URL. Must be a direct link to a file. "
                                           "Example: http://example.com/file.mp3")
        
        # Check if file type is valid
        directory = VALID_FILETYPES.get(extension)
        if not directory:
            # Fails if file type is not defined in VALID_FILETYPES
            raise discord.DiscordException(f"Invalid file type. Must be one of: **{file_types}**")
        
        # Attempt to download file
        sound_file = await self.download_from_url(url)
        return directory, file_name, extension, sound_file

    @commands.command(name="dl")
    async def dl(self, ctx: commands.Context, url: str=None) -> None:
        """Lazy download sound command.

        Depending on arguments received, calls either !ytdl or 
        
        Parameters
        ----------
        ctx : commands.Context
            Discord Context object
        url : str, optional
            Optional HTTP(s) URL to sound file. 
            Can not be None if message has no attachment.
        """
        if ctx.message.attachments or url and any(filetype in url for filetype in self.VALID_FILE_TYPES):
            cmd = self.bot.get_command("add_sound")
            await ctx.invoke(cmd, url)
        elif url:
            cmd = self.bot.get_command("ytdl")
            await ctx.invoke(cmd, url)
        else:
            raise discord.DiscordException("A URL or attached file is required!")
    
    @commands.command(name="join", aliases=["combine"])
    async def join_sound_files(self, ctx: commands.Context, file_1: str, file_2: str) -> None:
        """Joins two sound files together
        
        Parameters
        ----------
        ctx : commands.Context
            Discord context
        file_1 : str
            Filename of first sound (DON'T INCLUDE EXTENSION)
        file_2 : str
            Filename of second sound
        
        Raises
        ------
        AttributeError
            Raised if args to either file_1 or file_2 does
            not match a sound currently added to the soundboard.
        FileNotFoundError
            Raised if a converted .wav file cannot be found
        FileExistsError
            Raised if attempting to combine two files that have
            already been combined previously. 
        """

        infile_1 = None
        infile_2 = None
        for folder in self.sub_dirs:
            for sound in folder.sound_list:
                if file_1 == sound:
                    infile_1 = (folder.folder, sound)
                elif file_2 == sound:
                    infile_2 = (folder.folder, sound)
                if infile_1 and infile_2:
                    break
        if not infile_1 or not infile_2:
            raise AttributeError("Could not find file ")
        
        def convert(directory: str, filename: str, to_wav: bool) -> str:
            directory = f"{directory}/" if directory else ""
            in_ext = "mp3" if to_wav else "wav"
            out_ext = "wav" if to_wav else "mp3"
            temp = "_temp_" if to_wav else ""
            f = f"sounds/{directory}{filename}.{in_ext}"
            new = f"sounds/{directory}{temp}{filename}.{out_ext}"
            if to_wav:
                cmd = f'ffmpeg -i "{f}" -acodec pcm_u8 -ar 44100 "{new}"'
            else:
                cmd = f'ffmpeg -i "{f}" -acodec libmp3lame -ab 128k "{new}"'
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).wait()
            return new
        
        # Convert mp3 files to wav so the wave module can interact with them
        infile_1_name = await self.bot.loop.run_in_executor(None, convert, *infile_1, True)
        infile_2_name = await self.bot.loop.run_in_executor(None, convert, *infile_2, True)

        def join_wavs(file_1: str, file_1_orig: str, file_2:str, file_2_orig: str) -> Tuple[str, str]:
            if not Path(file_1).exists() and not Path(file_2).exists():
                raise FileNotFoundError("Some nice error text goes here")

            # Get wave file data
            wav_data = []
            for f in [file_1, file_2]:
                with wave.open(f, "rb") as w:
                    wav_data.append([w.getparams(), w.readframes(w.getnframes())])
            
            # Filenames. NOTE: This is ugly as hell
            joined_filename = f"{file_1_orig}_{file_2_orig}"
            filepath_base = f"sounds/{file_1_orig}_{file_2_orig}"
            filepath_wav = f"{filepath_base}.wav"
            filepath_mp3 = f"{filepath_base}.mp3"

            # Check if a file with the same name already exists
            if Path(filepath_mp3).exists():
                raise FileExistsError("File already exists")
            
            # Join wave files
            with wave.open(filepath_wav, "wb") as wavfile:
                wavfile.setparams(wav_data[0][0])
                wavfile.writeframes(wav_data[0][1])
                wavfile.writeframes(wav_data[1][1])
            
            # Return filename and relative filepath
            return joined_filename, filepath_wav
        
        # Combine wavs
        try:
            joined_filename_wav, joined_filepath_wav = join_wavs(infile_1_name, file_1, infile_2_name, file_2)
        except FileExistsError:
            raise
        except Exception:
            await ctx.send("Something went wrong.")

        finally:
            # Delete all temporary files afterwards
            os.remove(infile_1_name)
            os.remove(infile_2_name)
            
        # Convert 
        if joined_filename_wav:
            await self.bot.loop.run_in_executor(None, convert, "", joined_filename_wav, False)
            await ctx.send(f"Combined **{file_1}** & **{file_2}**! New sound: **{joined_filename_wav}**")
        
        # Delete wav version of joined file
        if Path(joined_filepath_wav).exists():
            os.remove(joined_filepath_wav)