import asyncio
import glob
import os
import random
import subprocess
import wave
import json
from collections import deque
from functools import partial
from itertools import islice, chain, count
from pathlib import Path
from queue import Queue
from typing import Iterator, Optional, Tuple, DefaultDict, Dict, Union, List
from urllib.parse import urlparse
from collections import defaultdict
from datetime import datetime
from contextlib import suppress
from time import time
import sys
from utils.converters import URLConverter, SoundURLConverter

import discord
import gtts
import youtube_dl
from async_timeout import timeout
from discord.ext import commands
from discord.opus import load_opus
from pathvalidate import sanitize_filename
from youtube_dl import YoutubeDL

from utils.checks import admins_only
from utils.messaging import wait_for_user_reply
from utils.exceptions import CommandError, VoiceConnectionError, InvalidVoiceChannel 
from cogs.base_cog import BaseCog

from config import SOUND_DIR, SOUND_SUB_DIRS, DOWNLOADS_DIR, YTDL_DIR, TTS_DIR, SOUNDLIST_FILE_LIMIT

ytdlopts = {
    'format': 'bestaudio/best', # Try format "250" ?
    'outtmpl': f'{YTDL_DIR}/%(title)s.%(ext)s',
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
    'before_options': "-nostdin -reconnect 1 -reconnect_at_eof 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    'options': '-vn'
}

ytdl = YoutubeDL(ytdlopts)

VALID_FILE_TYPES = ["mp3", ".mp4", ".webm", ".wav"] # this is probably useless
FILETYPES = {".mp3", ".wav", ".m4a", ".webm", ".mp4"}


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
    async def create_local_source(cls, ctx, subdir: str, filename: str):
        # Get path to local sound file
        path = glob.glob(f"{subdir}/{filename}*")[0]

        # Send add-to-queue confirmation
        await ctx.send(f"```\nAdded {filename} to the Queue.\n```", delete_after=10)

        return cls(discord.FFmpegPCMAudio(path), data={"title":filename}, requester=ctx.author)

    @classmethod
    async def regather_stream(cls, data, *, loop):
        """Used for preparing a stream, instead of downloading.

        Since Youtube Streaming links expire."""
        loop = loop or asyncio.get_event_loop()
        requester = data['requester']

        to_run = partial(ytdl.extract_info, url=data['webpage_url'], download=False)
        data = await loop.run_in_executor(None, to_run)
        
        return cls(discord.FFmpegPCMAudio(data['url'], **ffmpegopts), data=data, requester=requester)


class AudioPlayer:
    def __init__(self, ctx):
        self.bot = ctx.bot
        self.guild = ctx.guild
        self.channel = ctx.channel
        if ctx.cog.qualified_name == "SoundCog":
            self.cog = ctx.cog
        else:
            self.cog = self.bot.get_cog("SoundCog")

        self.created_at = datetime.now()

        self.queue = asyncio.Queue()
        self.next = asyncio.Event()

        self.np = None
        self.volume = 1
        self.current = None

        self.timeout_duration = 60.0

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


class SoundDirectory:
    """
    Represents a subdirectory of the base sound directory defined
    in `config.py`.
    """

    def __init__(self, 
                 folder: str, 
                 header: str, 
                 aliases: list, 
                 path: str, 
                 color: Optional[Union[str, int]]=None) -> None:
        self.folder = folder
        self.header = header # This attribute is honestly pretty terrible
        self.aliases = aliases
        self.path = path
        self.color = color
        self.last_modified = None
        self._sound_list = None

    @property
    def sound_list(self) -> list:
        modified = os.path.getmtime(self.path)
        if not self._sound_list or modified != self.last_modified:
            self.last_modified = modified
            self._sound_list = {sound_file: self.path for sound_file in [
                i.rsplit(".", 1)[0]
                for i in os.listdir(self.path)
                if any(i.endswith(ext) for ext in VALID_FILE_TYPES) # Only include known compatible containers
                ]
                }
        return self._sound_list


class SoundCog(BaseCog):
    """Soundboard commands"""

    EMOJI = ":speaker:"

    DIRS = [d.path for d in SOUND_SUB_DIRS]

    YTDL_MAXSIZE = 10000000 # 10 MB

    def __init__(self, bot: commands.Bot) -> None:
        super().__init__(bot)
        
        if sys.platform == "linux":
            load_opus("libopus.so.0")
        
        # Create SoundDirectory instance for each subdirectory
        self.sub_dirs = [
                         SoundDirectory(
                         folder=subdir.folder,
                         header=subdir.folder.upper(),
                         aliases=subdir.aliases,
                         path=subdir.path,
                         color=self.generate_hex_color_code(subdir.folder))
                         for subdir in SOUND_SUB_DIRS
                         ]
        self._sub_dirs_last_modified = {}
        
        # Per-guild audio players. Key: Guild ID
        self.players: Dict[int, AudioPlayer] = {}

        # Number of sounds played by guilds in the current session
        self.played_count: DefaultDict[int, int] = defaultdict(int) # Key: Guild ID. Value: n times played

        self._sound_list = {}

    @property
    def sound_list(self) -> list:
        """
        Returns list of files in the sound folder provided on class instantiation.
        
        Returns:
            sound_list: list of file names, all lowercase and without the .mp3 file extension.
        
        Raises Exception if the folder contains no .mp3 files.
        """
        for sf in self.sub_dirs:
            try:
                if self._sub_dirs_last_modified[sf.path] == sf.last_modified:
                    continue
            except KeyError:
                pass
            self._sound_list.update(sf.sound_list)
            self._sub_dirs_last_modified[sf.path] = sf.last_modified
        if not self._sound_list:
            raise ValueError("No local sound files exist!")
        return self._sound_list

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
    @admins_only()
    async def show_players(self, ctx: commands.Context) -> None:
        """ADMIN ONLY: Shows active Audio Players"""
        players = "\n".join(
            [f"{str(self.bot.get_guild(gid))}" for gid in self.players]
        )
        if players:
            await ctx.send(players)
        else:
            await ctx.send("No active audio players.")

    @commands.command(name="played")
    @admins_only()
    async def times_played_session(self, ctx: commands.Context) -> None:
        """
        Displays current number of sounds played by guilds in the
        current bot session
        """
        out = "\n".join([f"{self.bot.get_guild(k)}: {v}" for k, v in self.played_count.items()])
        await self.send_text_message(out, ctx)

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

        # If bot is restarted while connected to a voice channel, 
        # it can sometimes get "stuck" in a channel in a state where
        # any attempts to play sound is unsuccessful
        if not vc and self.bot.user.id in [user.id for user in channel.members]:
            await channel.connect() # Try to connect
            await ctx.invoke(self.stop) # Immediately issue !stop command, removing bot user from channel

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
        # Check if downloading is allowed
        if ctx.invoked_with == "ytdl":
            await self.check_downloads_permissions(add_msg=
                "Use **`!play`** or **`!yt`** instead.")

        vc = ctx.voice_client

        if not vc:
            await ctx.invoke(self.connect, channel=voice_channel)

        player = self.get_player(ctx)

        arg = " ".join(args)

        # Play audio from online source
        if urlparse(arg).scheme in ["http", "https"]:
            download = True if ctx.invoked_with == "ytdl" else False
            source = await YTDLSource.create_source(ctx, arg, loop=self.bot.loop, download=download)
            await player.queue.put(source)

        # Play local file
        else:
            # Try to parse provided sound name
            try:
                if arg:
                    sound_name = arg
                    try:
                        subdir = self.sound_list[sound_name]
                    except KeyError:
                        raise KeyError(f"Could not find sound by the name of **`{arg}`**") 
                    subdir = self.sound_list[sound_name]
                else:
                    # Select random sound if no argument
                    subdir, sound_name = random.choice(self.sound_list.items())
            
            # Attempt to suggest sound files with similar names if no results
            except AttributeError:
                embeds = await ctx.invoke(self.search, arg, rtn=True)
                dym = "Did you mean:" if embeds else ""
                await ctx.send(f"No sound with name **`{arg}`**. {dym}")
                for embed in embeds:
                    await ctx.send(embed=embed)
                return

            source = await YTDLSource.create_local_source(ctx, subdir, sound_name)
            await player.queue.put(source)

        # Increment played count for guild
        self.played_count[ctx.guild.id] += 1

    @commands.command(name="rplay")
    async def remoteplay(self, ctx: commands.Context, channel: commands.VoiceChannelConverter, *args) -> None:
        """`!play` in a specific channel."""
        await ctx.invoke(self.play, *args, voice_channel=channel)

    @commands.command(name="stop", aliases=["s"])
    async def stop(self, ctx: commands.Context) -> None:
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
    @admins_only()
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
    @admins_only()
    async def destroy_player(self, ctx) -> None:
        vc = ctx.voice_client

        if not vc or not vc.is_connected():
            return await ctx.send('I am not currently playing anything!', delete_after=20)

        await self.cleanup(ctx.guild)

    @commands.command(name="soundlist",
                      aliases=["sounds"], description='Prints a list of all sounds on the soundboard.')
    @commands.cooldown(rate=1, per=10, type=commands.BucketType.user)
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

        # Formatted string of sound categories
        categories = "\n".join(
            [f"**`{sd.folder}`**" for sd in self.sub_dirs if sd.sound_list]
            )
        
        # Raise exception if all sound directories are empty
        if not categories:
            raise AttributeError("Soundboard has no sound files!")
        
        # Prompt user to specify category if message lacks category argument
        if not category:
            await self.send_embed_message(ctx,
                                          header="Categories", 
                                          text=categories)
            await ctx.send(f"\nType **`!{ctx.invoked_with}`** + **`<category>`**")
            self.reset_command_cooldown(ctx)
            return

        # Directory names are all lowercase
        category = category.lower()

        # Find subdirectory matching `category` argument
        for sub_dir in self.sub_dirs:
            if category in sub_dir.aliases:
                break
        # Raise exception if no sound directory matches category
        else:
            raise CommandError(f"No such category **`{category}`**.\n"
                               f"Categories: {categories}")
        
        # Compile list of sounds
        _out = [sound for sound in sub_dir.sound_list]

        # Send large directory sound lists as DM
        if len(_out) > SOUNDLIST_FILE_LIMIT:
            msg = (  
            f"The **`{category}`** category contains {len(_out)} sound files. "
            f"It is recommended to try using the **`{self.bot.command_prefix}search`** command first.\n"
            f"Are you sure you want to show all sounds in this category?"
            )
            if not await wait_for_user_reply(ctx, msg, timeout=20.0):
                return await ctx.send("Aborting.")
            await ctx.send("Soundlist will be sent as DM.")
            channel = await ctx.message.author.create_dm()
        else:
            channel = None
        
        out = "\n".join(_out)
        
        if not out:
            return await ctx.send(
                f"Category **`{category}`** is empty!"
                )
        
        return await self.send_embed_message(
            ctx, sub_dir.header, out, color=sub_dir.color, channel=channel)

    @commands.command(name="search")
    async def search(self, 
                     ctx: commands.Context, 
                     *search_query: str, 
                     rtn: bool=False) -> Optional[List[discord.Embed]]:
        # Join args into space-separated search query string
        search_query = " ".join(search_query)
        if not search_query or all(char == " " for char in search_query):
            raise CommandError("Search query cannot be an empty string.")
        
        # Get search results formatted as Discord embed objects
        embeds = []
        for sf in self.sub_dirs:
            _out = [sound for sound in sf.sound_list if search_query.lower() in sound.lower()]
            if _out:
                _out_str = "\n".join(_out)
                _rtn_embeds = await self.send_embed_message(ctx, sf.header, _out_str, color=sf.color, return_embeds=True)
                embeds.extend(_rtn_embeds)

        # Return embeds if enabled
        if rtn:
            return embeds

        # Post search results to ctx.channel otherwise
        if embeds:
            for embed in embeds:
                await ctx.send(embed=embed)
        else:
            await ctx.send("No results")

    @commands.command(name="queue")
    async def show_queue(self, ctx: commands.Context) -> None:
        """Display soundboard queue."""
        vc = ctx.voice_client

        if not vc or not vc.is_connected():
            return await ctx.send("I am not currently connected to a voice channel!", delete_after=5)

        player = self.get_player(ctx)
        if player.queue.empty():
            return await ctx.send("Queue is empty!")

        upcoming = list(islice(player.queue._queue, 0, 5))

        out_msg = "\n".join(f'{idx}. **`{up["title"]}`**' for idx, up in enumerate(upcoming, 1))

        await self.send_embed_message(ctx, "Queue", out_msg, color="red")


    @commands.command(name="tts",
                      aliases=["texttospeech", "text-to-speech"])
    async def texttospeech(self, ctx: commands.Context, text: str, language: str="en", filename: Optional[str]=None) -> None:
        """Text-to-speech
        """

        # gTTS exception handling.
        # The language list has a tendency to break, and requires an update of the gTTS library
        try:
            valid_langs = gtts.lang.tts_langs()
        except:
            await self.send_log(f"**URGENT**: Update gTTS. <pip install -U gTTS> {self.AUTHOR_MENTION}")
            raise discord.DiscordException("Google Text-to-Speech needs to be updated. Try again later.")

        # User error and help arguments
        if not text:
            return await self.send_error_msg(ctx, "Text for TTS is a required argument.")

        elif text in ["languages", "lang", "options"]:
            _langs = [
                    f"`{lang_short}`{self.EMBED_FILL_CHAR*(8-len(lang_short))}"
                    f"{lang_long}" for lang_short, lang_long in valid_langs.items()
                    ]
            langs = "\n".join(_langs)
            await self.send_embed_message(ctx, "Code\tLanguage", langs, keep_header=True)
            return

        # Get tts object
        tts = gtts.gTTS(text=text, lang=language)

        await ctx.trigger_typing()

        # Check argument to param filename
        if filename:
            filename = sanitize_filename(filename)    
        # Use first word of text if no filename
        else:
            filename = sanitize_filename(text.split(" ")[0])

        # Check filename. If filename is taken or invalid, generate filename from text    
        sound_name = self.get_unique_filename(TTS_DIR, filename, ".mp3")

        # Save mp3 file
        to_run = partial(tts.save, f"{TTS_DIR}/{sound_name}.mp3")
        await self.bot.loop.run_in_executor(None, to_run)

        # Confirm creation of file
        await ctx.send(f'TTS audio file created: **`{sound_name}`**')

        # Try to play created sound file in author's voice channel afterwards
        with suppress(AttributeError):
            if ctx.message.author.voice.channel:
                cmd  = self.bot.get_command('play')
                await ctx.invoke(cmd, sound_name)

    @commands.command(name="add_sound")
    async def add_sound(self, ctx: commands.Context, url: str=None, filename: str=None) -> None:
        """Downloads a sound file from msg attachment or URL
        
        Parameters
        ----------
        ctx : `commands.Context`
            Discord Context object
        url : `str`, optional
            HTTP(s) URL of file. 
            If message has no attachment, command will raise
            exception if URL is None.
        """

        # Check if downloading is allowed
        await self.check_downloads_permissions()
        
        # Raise exception if message has no attachment and no URL was passed in
        if not ctx.message.attachments and not url:
            return await self.send_error_msg(ctx, "A file attachment or file URL is required!")

        # Use attachment URL if possible
        if ctx.message.attachments:
            attachment = ctx.message.attachments[0]
            filename, url = url, attachment.url

        # Download and save sound file
        try:
            filename = await self._do_download_sound(ctx, url, filename=filename)        
        
        except AttributeError:
            return await self.send_error_msg(ctx,
                "Invalid URL. Must be a direct link to a file. "
                "Example: http://example.com/file.mp3")        
        
        except ValueError:
            return await self.send_error_msg(ctx,
                f"Invalid file type. Must be one of: **{FILETYPES}**")
        
        else:
            # Post download confirmation
            await ctx.send(f"Saved file **`{filename}`**")
            
            # Play downloaded sound if ctx.author is in a voice channel
            if hasattr(ctx.author.voice, "channel"):
                await ctx.invoke(self.play, filename)

    async def _do_download_sound(self, ctx: commands.Context, url: str, *, filename: str=None) -> str:
        """Attempts to download sound file from URL.
        
        Fails if file already exists or file is not a 
        recognized filetype.
        
        Parameters
        ----------
        ctx : `commands.Context`
            Discord context
        url : `str`
            HTTP(s) URL of target file
        """       
        # Get filename and extension
        fname, ext = await self.get_filename_extension_from_url(url)
        if not filename:
            filename = fname
        else:
            filename = sanitize_filename(filename)
        
        if not ext:
            raise AttributeError

        # Check if file type is valid
        if ext not in FILETYPES:
            raise ValueError
        
        # Get file path
        filename = self.get_unique_filename(DOWNLOADS_DIR, filename, ext)
        filepath = f"{DOWNLOADS_DIR}/{filename}{ext}"           
        
        # Attempt to download file
        sound_file = await self.download_from_url(ctx, url)

        # Save file
        with open(filepath, "wb") as f:
            f.write(sound_file.getvalue())

        # Log downloaded file
        await self.log_file_download(ctx, url=url, filename=f"{filename}.{ext}")        
        
        return filename
    
    def get_unique_filename(self, directory: str, filename: str, ext: str=None) -> str:
        for i in count():
            # Increment until a unique filename is found
            if not i:
                i = ""
            fname = f"{filename}{i}"
            filepath = f"{directory}/{fname}{ext}"
            if not Path(filepath).exists():
                return fname

    @commands.command(name="dl")
    async def dl(self, ctx: commands.Context, url: URLConverter=None) -> None:
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
                url.path.lower().endswith(filetype) 
                for filetype in VALID_FILE_TYPES):
            cmd = self.bot.get_command("add_sound")
            await ctx.invoke(cmd, url)
        
        elif url:
            cmd = self.bot.get_command("ytdl")
            await ctx.invoke(cmd, url)
        
        else:
            raise discord.DiscordException("A URL or attached file is required!")

    @commands.command(name="combine")
    @admins_only()
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
