import asyncio
import glob
import os
import random
import subprocess
import wave
import json
from collections import deque
from functools import partial
from itertools import islice, chain
from pathlib import Path
from queue import Queue
from typing import Iterator, Optional, Tuple, DefaultDict, Dict
from urllib.parse import urlparse
from collections import defaultdict

import discord
import gtts
import youtube_dl
from async_timeout import timeout
from discord import opus
from discord.ext import commands
from pathvalidate import sanitize_filename
from youtube_dl import YoutubeDL

from ext.checks import is_admin
from cogs.base_cog import BaseCog, InvalidFiletype
from ext_module import ExtModule
from utils.config import SOUND_DIR

ytdlopts = {
    'format': 'bestaudio/best',
    'outtmpl': 'sounds/ytdl/%(title)s.%(ext)s',
    #'restrictfilenames': True, # Leads to markdown formatting issues when enabled
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0'  # ipv6 addresses cause issues sometimes
}

ffmpegopts = {
    'before_options': '-nostdin',
    'options': '-vn'
}

ytdl = YoutubeDL(ytdlopts)

VALID_FILE_TYPES = ["mp3", ".mp4", ".webm", ".wav"] # this is probably useless

class VoiceConnectionError(commands.CommandError):
    """Custom Exception class for connection errors."""


class InvalidVoiceChannel(VoiceConnectionError):
    """Exception for cases of invalid Voice Channels."""

class YTDLSource(discord.PCMVolumeTransformer):

    def __init__(self, source, *, data, requester):
        super().__init__(source)
        self.requester = requester

        self.title = data.get("title")
        self.web_url = data.get("webpage_url")

    def __getitem__(self, item: str):
        """Allows us to access attributes similar to a dict.

        This is only useful when you are NOT downloading.
        """
        return self.__getattribute__(item)

    @classmethod
    async def create_source(cls, ctx, search: str, *, loop, download=False):
        loop = loop or asyncio.get_event_loop()

        to_run = partial(ytdl.extract_info, url=search, download=download)
        data = await loop.run_in_executor(None, to_run)

        if "entries" in data:
            # take first item from a playlist
            data = data["entries"][0]

        await ctx.send(f"```\nAdded {data['title']} to the Queue.\n```", delete_after=10)

        if download:
            source = ytdl.prepare_filename(data)
        else:
            return {"webpage_url": data["webpage_url"], "requester": ctx.author, "title": data["title"]}

        return cls(discord.FFmpegPCMAudio(source), data=data, requester=ctx.author)

    @classmethod
    async def create_local_source(cls, ctx, subdir: str, sound_name: str, *, loop):
        loop = loop or asyncio.get_event_loop()
        # Get path to local sound file
        path = glob.glob(f"sounds/{subdir}*{sound_name}*")[0]
        await ctx.send(f"```\nAdded {sound_name} to the Queue.\n```", delete_after=10)
        return cls(discord.FFmpegPCMAudio(path), data={"title":sound_name}, requester=ctx.author)

    @classmethod
    async def regather_stream(cls, data, *, loop):
        """Used for preparing a stream, instead of downloading.

        Since Youtube Streaming links expire."""
        loop = loop or asyncio.get_event_loop()
        requester = data['requester']

        to_run = partial(ytdl.extract_info, url=data['webpage_url'], download=False)
        data = await loop.run_in_executor(None, to_run)

        return cls(discord.FFmpegPCMAudio(data['url']), data=data, requester=requester)


class AudioPlayer:
    def __init__(self, ctx):
        self.bot = ctx.bot
        self.guild = ctx.guild
        self.channel = ctx.channel
        self.cog = ctx.cog

        self.queue = asyncio.Queue()
        self.next = asyncio.Event()

        self.np = None
        self.volume = 1
        self.current = None

        self.timeout_duration = 60

        ctx.bot.loop.create_task(self.player_loop())

    async def player_loop(self):
        await self.bot.wait_until_ready()

        while not self.bot.is_closed():
            self.next.clear()

            try:
                async with timeout(self.timeout_duration):
                    source = await self.queue.get()
            except asyncio.TimeoutError:
                return self.destroy(self.guild)

            if not isinstance(source, YTDLSource):
                try:
                    source = await YTDLSource.regather_stream(source, loop=self.bot.loop)
                except:
                    await self.channel.send("There was an error processing your song")
                    continue

            source.volume = self.volume
            self.current = source

            self.guild.voice_client.play(source, after=lambda _: self.bot.loop.call_soon_threadsafe(self.next.set))
            self.np = await self.channel.send(f"```\nNow playing: {source.title}```")
            await self.next.wait()

            source.cleanup()
            self.current = None

            try:
                await self.np.delete()
            except discord.HTTPException:
                pass

    def destroy(self, guild):
        """Disconnect and cleanup the player."""
        return self.bot.loop.create_task(self.cog.cleanup(guild))


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
        return sorted(
            [
            i.rsplit(".", 1)[0]
            for i in os.listdir(f"{self.BASE_DIR}/{self.folder}")
            if any([i.endswith(ext) for ext in VALID_FILE_TYPES]) # Only include known compatible containers
            ],
            key=lambda f: f.lower()) # Sort case insensitive


class SoundCog(BaseCog):
    """Cog for the soundboard feature"""
    VALID_FILE_TYPES = ["mp3", ".mp4", ".webm"] # this is probably useless
    YTDL_MAXSIZE = 10000000 # 10 MB
    SOUND_DIR_IGNORE = ["emptytest", "original", "cleaned"]
    DOWNLOADS_DIR = f"{SOUND_DIR}/downloads"

    def __init__(self, bot: commands.Bot, log_channel_id: int) -> None:
        super().__init__(bot, log_channel_id)

        # Find all subdirectories
        subfolders = [
            f.name for f in os.scandir(SOUND_DIR)
            if f.is_dir() and f.name not in self.SOUND_DIR_IGNORE
        ]

        # Sound file directories
        self.sub_dirs = [
                         SoundFolder(sfolder, sfolder.capitalize(),
                         color=self.generate_hex_color_code(sfolder))
                         for sfolder in subfolders
                         ]

        # Per-guild audio players
        self.players: Dict[int, AudioPlayer] = {}

        # Number of sounds played by guilds in the current session
        self.played_count: DefaultDict[int, int] = defaultdict(int) # Key: Guild ID. Value: n times played
        
        # Monitor active players
        #self.bot.loop.create_task(self.monitor_players())

        self.setup_directories()

    async def monitor_players(self) -> None:
        while True:
            with open("db/players.json", "w") as f:
                json.dump([str(player.guild) for player in self.players.values()], f)
            await asyncio.sleep(10)

    def setup_directories(self) -> None:
        """Creates directories neccessary for soundboard commands"""
        # Base sound directory
        paths = [
            SOUND_DIR,
            f"{SOUND_DIR}/downloads",
            f"{SOUND_DIR}/downloads/wav",
            f"{SOUND_DIR}/ytdl/",
            f"{SOUND_DIR}/general",
            f"{SOUND_DIR}/yeah"
        ]
        for path in paths:
            if not Path(path).exists():
                os.mkdir(path)

    @property
    def sound_list(self) -> list:
        """
        Returns list of files in the sound folder provided on class instantiation.
        
        Returns:
            sound_list: list of file names, all lowercase and without the .mp3 file extension.
        
        Raises Exception if the folder contains no .mp3 files.
        """

        s = list(chain(*[sf.sound_list for sf in self.sub_dirs]))
        if not s:
            raise Exception("No mp3 files in the given folder")
        return s

    async def cleanup(self, guild):
        try:
            await guild.voice_client.disconnect()
        except AttributeError:
            pass

        try:
            del self.players[guild.id]
        except KeyError:
            pass

    def get_player(self, ctx: commands.Context) -> AudioPlayer:
        """Retrieve the guild player, or generate one."""
        try:
            player = self.players[ctx.guild.id]
        except KeyError:
            player = AudioPlayer(ctx)
            self.players[ctx.guild.id] = player
        return player

    @commands.command(name="players")
    @is_admin()
    async def show_players(self, ctx: commands.Context) -> None:
        """ADMIN ONLY: Shows active Audio Players"""
        players = [f"{str(self.bot.get_guild(gid))}" for gid in self.players]
        players = "\n".join(players)
        if players:
            await ctx.send(players)
        else:
            await ctx.send("No active audio players")

    @commands.command(name="played")
    @is_admin()
    async def times_played_session(self, ctx: commands.Context) -> None:
        """
        Displays current number of sounds played by guilds in the
        current bot session
        """
        out = "\n".join([f"{self.bot.get_guild(k)}: {v}" for k, v in self.played_count.items()])
        await self.send_text_message(ctx, out)

    @commands.command(name="connect", aliases=["join"])
    async def connect(self, ctx, *, channel: discord.VoiceChannel=None):
        """Connect to voice.

        Parameters
        ------------
        channel: discord.VoiceChannel [Optional]
            The channel to connect to. If a channel is not specified, an attempt to join the voice channel you are in
            will be made.

        This command also handles moving the bot to different channels.
        """
        if not channel:
            try:
                channel = ctx.author.voice.channel
            except AttributeError:
                raise InvalidVoiceChannel('No channel to join. Please either specify a valid channel or join one.')

        vc = ctx.voice_client

        # If bot is restarted while connected, it can sometimes get "stuck" in a channel
        if not vc and self.bot.user.id in [user.id for user in channel.members]:
            await channel.connect()
            await ctx.invoke(self.stop)

        if vc:
            if vc.channel.id == channel.id:
                return
            try:
                await vc.move_to(channel)
            except asyncio.TimeoutError:
                raise VoiceConnectionError(f'Moving to channel: <{channel}> timed out.')
        else:
            try:
                await channel.connect()
            except asyncio.TimeoutError:
                raise VoiceConnectionError(f'Connecting to channel: <{channel}> timed out.')

    @commands.command(name="play", aliases=["ytdl", "yt"])
    async def play(self, ctx: commands.Context, *args, voice_channel: commands.VoiceChannelConverter=None) -> None:
        """
        Plays sound in message author's voice channel

        args:
            *args: Name of sound file to play. If len(args)>1, args are joined into
            single string separated by spaces.
        """
        vc = ctx.voice_client

        if not vc:
            await ctx.invoke(self.connect, channel=voice_channel)

        player = self.get_player(ctx)

        async def parse_sound_name(arg) -> Tuple[str, str]:
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

        uri = " ".join(args)

        # Play audio from online source
        if urlparse(uri).scheme in ["http", "https"]:
            download = True if ctx.invoked_with == "ytdl" else False
            source = await YTDLSource.create_source(ctx, uri, loop=self.bot.loop, download=download)
            await player.queue.put(source)

        # Play local file
        else:
            uri = uri.lower()      
            # Try to parse provided sound name
            try:
                subdir, sound_name = await parse_sound_name(uri)
            # Suggest sound files with similar names if no results
            except:
                # TODO: Do some dumb shit with partial methods
                embeds = await ctx.invoke(self.search, uri, rtn=True)
                dym = "Did you mean:" if embeds else ""
                await ctx.send(f"No sound with name **`{uri}`**. {dym}")
                for embed in embeds:
                    await ctx.send(embed=embed)
                return
            
            source = await YTDLSource.create_local_source(ctx, subdir, sound_name, loop=self.bot.loop)
            await player.queue.put(source)
        
        # Increment played count for guild
        self.played_count[ctx.guild.id] += 1

    @commands.command(name="rplay")
    async def remoteplay(self, ctx: commands.Context, channel: commands.VoiceChannelConverter, *args) -> None:
        print("yeah")
        await ctx.invoke(self.play, *args, voice_channel=channel)

    @commands.command(name="stop", aliases=["s"])
    async def stop(self, ctx: commands.Context) -> Optional[str]:
        player = self.get_player(ctx)
        vc = ctx.voice_client

        if vc and vc.is_connected() and not player.queue.empty():
            await ctx.invoke(self.skip)
        else:
            await self.cleanup(ctx.guild)

    @commands.command(name='skip')
    async def skip(self, ctx):
        """Skip the song."""
        vc = ctx.voice_client

        if not vc or not vc.is_connected():
            return await ctx.send('I am not currently playing anything!', delete_after=5)

        if vc.is_paused():
            pass
        elif not vc.is_playing():
            return

        vc.stop()
        await ctx.send(f'**`{ctx.author}`**: Skipped the song!')

    @commands.command(name="volume", aliases=["vol"])
    @is_admin()
    async def change_volume(self, ctx, *, vol: int):
        """Sets player volume (1-100)"""
        vc = ctx.voice_client

        if not vc or not vc.is_connected():
            return await ctx.send('I am not currently connected to voice!', delete_after=5)

        if not 0 < vol < 101:
            return await ctx.send('Please enter a value between 1 and 100.')

        player = self.get_player(ctx)

        if vc.source:
            vc.source.volume = vol / 100

        player.volume = vol / 100
        await ctx.send(f'**`{ctx.author}`**: Set the volume to **{vol}%**')

    @commands.command(name="now_playing", aliases=["np"])
    async def now_playing(self, ctx) -> None:
        vc = ctx.voice_client

        if not vc or not vc.is_connected():
            return await ctx.send("I am not currently connected to voice!", delete_after=5)

        player = self.get_player(ctx)
        if not player.current:
            return await ctx.send("I am not currently playing anything!")

        try:
            await player.np.delete()
        except discord.HTTPException:
            pass

        player.np = await ctx.send(f'**Now Playing:** `{vc.source.title}` '
                                   f'requested by `{vc.source.requester}`')

    @commands.command(name="destroy", aliases=["quit"])
    @is_admin()
    async def destroy_player(self, ctx) -> None:
        vc = ctx.voice_client

        if not vc or not vc.is_connected():
            return await ctx.send('I am not currently playing anything!', delete_after=20)

        await self.cleanup(ctx.guild)

    @commands.command(name="soundlist",
                      aliases=["sounds"], description='Prints a list of all sounds on the soundboard.')
    async def soundlist(self, ctx: commands.Context, category: Optional[str]=None) -> None:
        """Lists all available sound files
        
        Parameters
        ----------
        ctx : commands.Context
            Discord Context
        category : `str`, optional
            Sound category. 
            See SoundCog.sub_dirs for available categories.
        
        Raises
        ------
        discord.DiscordException
            Raised if attempting to display all sound files at once.
        """
        def get_category(category: str) -> Optional[str]:
            if category is not None:
                if category in ["yt", "youtube", "ytdl"]:
                    return "ytdl"
                elif category in ["tts", "texttospeech"]:
                    return "tts"
                elif category in [sf.folder for sf in self.sub_dirs]:
                    return category

        # Parse argument `category`
        if not category:
            categories = ", ".join([f"**`{sf.folder}`**" for sf in self.sub_dirs])
            await ctx.send(f"Specify a category.\nType **`!{ctx.invoked_with}`** + {categories}")
            return

        category = get_category(category.lower())

        # Send sound list
        for sf in self.sub_dirs:
            if sf.folder == category or not category:
                _out = ""
                for sound in sf.sound_list:
                    _out += f"{sound}\n"
                await self.send_chunked_embed_message(ctx, sf.header, _out, color=sf.color)
                break

    @commands.command(name="search")
    async def search(self, ctx: commands.Context, *search_query: str, rtn: bool=False) -> None:
        search_query = " ".join(search_query)
        embeds = []

        for sf in self.sub_dirs:
            _out = []
            for sound in sf.sound_list:
                if search_query.lower() in sound.lower():
                    # Append sound name to _out string
                    _out.append(sound)
            if _out:
                _out_str = "\n".join(_out)
                _rtn_embeds = await self.send_chunked_embed_message(ctx, sf.header, _out_str, color=sf.color, return_embeds=rtn)
                for embed in _rtn_embeds:
                    embeds.append(embed)
        
        # Return embeds if enabled
        if rtn:
            return embeds
        
        # Post results
        if embeds:
            for embed in embeds:
                await ctx.send(embed=embed)
        else:
            await ctx.send("No results")

    @commands.command(name="queue")
    async def show_queue(self, ctx) -> Optional[str]:
        vc = ctx.voice_client

        if not vc or not vc.is_connected():
            return await ctx.send("I am not currently connected to a voice channel!", delete_after=5)

        player = self.get_player(ctx)
        if player.queue.empty():
            return await ctx.send("Queue is empty!")

        upcoming = list(islice(player.queue._queue, 0, 5))

        out_msg = "\n".join(f'**`{up["title"]}`**' for up in upcoming)
        embed = await self.get_embed(ctx, fields=[self.EmbedField("Queue", out_msg)], color="red")
        await ctx.send(embed=embed)

    @commands.command(name="tts",
                      aliases=["texttospeech", "text-to-speech"])
    async def texttospeech(self, ctx: commands.Context, text: str, language: str="en", filename: Optional[str]=None) -> None:
        """Text-to-speech
        """
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
        if not text:
            raise discord.DiscordException("Text for TTS is a required argument.")

        elif text in ["languages", "lang", "options"]:
            langs = [f"{lang_long}: {lang_short}" for lang_long, lang_short in valid_langs.items()]
            output = await self.format_output(langs, item_type="languages") # should be item_name/category smh
            await ctx.send(output)
            return

        # Get tts object
        tts = gtts.gTTS(text=text, lang=language)

        # Get filename
        if filename:
            sound_name = sanitize_filename(filename)
        else:
            sound_name = sanitize_filename(text.split(" ")[0])

        # Check if filename already exists
        if not Path(f"sounds/tts/{sound_name}.mp3").exists() or len(sound_name) <= 5:
            sound_name = sanitize_filename(text)
            if Path(f"sounds/tts/{sound_name}.mp3").exists():
                raise FileExistsError("Sound already exists.")

        # Save mp3 file
        tts.save(f"sounds/tts/{sound_name}.mp3")

        # Confirm creation of file
        await ctx.send(f'Sound created: **{sound_name}**')

        # Try to play created sound file in author's voice channel afterwards
        try:
            if ctx.message.author.voice.channel is not None:
                cmd  = self.bot.get_command('play')
                await ctx.invoke(cmd, sound_name)
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
        filename = await self._do_download_sound(url)

        await ctx.send(f"Saved file {filename}")

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
                ".mp3": f"{SOUND_DIR}/downloads",
                ".wav": f"{SOUND_DIR}/downloads/wav"
            }
        # Generate formatted string of valid file types
        file_types = ", ".join(VALID_FILETYPES.keys())

        # Get file extension
        filename, ext = await self.get_filename_extension_from_url(url)
        if not ext:
            raise discord.DiscordException("Invalid URL. Must be a direct link to a file. "
                                           "Example: http://example.com/file.mp3")

        # Check if file type is valid
        directory = VALID_FILETYPES.get(ext)
        if not directory:
            # Fails if file type is not defined in VALID_FILETYPES
            raise discord.DiscordException(f"Invalid file type. Must be one of: **{file_types}**")

        # Attempt to download file
        sound_file = await self.download_from_url(url)
        filepath = f"{directory}/{filename}{ext}"
        with open(filepath, "wb") as f:
            f.write(sound_file.getvalue())

        if ext in [".wav"]:
            filename = await self.convert_soundfile_to_mp3(directory, filename, ext, self.DOWNLOADS_DIR)
            return filename
    
    async def convert_soundfile_to_mp3(self, src_dir: str, filename: str, extension: str, dest_dir) -> None:
        """Converts a sound file to an .mp3 file, then deletes original file"""
        if extension not in [".wav"]:
            raise InvalidFiletype(f"Files with extension {extension} cannot be converted!")

        def convert(directory: str, filename: str, extension: str, dest_dir: str) -> str:
            f_base = f"{src_dir}/{filename}{extension}"
            f_mp3 = f"{dest_dir}/{filename}.mp3"

            cmd = f'ffmpeg -i "{f_base}" -acodec libmp3lame -ab 128k "{f_mp3}"'
            rtn = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).wait()
            if rtn == 0:
                os.remove(f_base)

        await self.bot.loop.run_in_executor(None, convert, src_dir, filename, extension, dest_dir)
        return filename
    
    @commands.command(name="dl")
    async def dl(self, ctx: commands.Context, url: str=None) -> None:
        """Lazy download sound command.

        Depending on arguments received, 
        calls either `!ytdl` or `!add_sound`
        
        Parameters
        ----------
        ctx : `commands.Context`
            Discord Context object
        url : `str`, optional
            Optional HTTP(s) URL to sound file. 
            Can not be None if message has no attachment.
        """
        if ctx.message.attachments or url and any(
                filetype in url for filetype in VALID_FILE_TYPES):
            cmd = self.bot.get_command("add_sound")
            await ctx.invoke(cmd, url)
        elif url:
            cmd = self.bot.get_command("ytdl")
            await ctx.invoke(cmd, url)
        else:
            raise discord.DiscordException("A URL or attached file is required!")

    @commands.command(name="combine")
    async def join_sound_files(self, ctx: commands.Context, file_1: str, file_2: str) -> None:
        """Combines two sound files
        
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

        # NOTE: ugly
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
            """Attempts to convert a file from .mp3 to .wav or vice versa"""
            directory = f"{directory}/" if directory else ""
            in_ext = "mp3" if to_wav else "wav"
            out_ext = "wav" if to_wav else "mp3"
            temp = "_temp_" if to_wav else ""
            f = f"{SOUND_DIR}/{directory}{filename}.{in_ext}"
            new = f"{SOUND_DIR}/{directory}{temp}{filename}.{out_ext}"
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
            filepath_base = f"{SOUND_DIR}/{file_1_orig}_{file_2_orig}"
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


