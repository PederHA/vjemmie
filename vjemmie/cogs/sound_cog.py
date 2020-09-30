import asyncio
import glob
import os
import random
import subprocess
import sys
import wave
from collections import defaultdict
from contextlib import suppress
from datetime import datetime
from functools import partial
from itertools import count, islice
from pathlib import Path
from typing import DefaultDict, Dict, List, Optional, Tuple, Union
from urllib.parse import urlparse

import discord
import gtts
import youtube_dl
from aiofile import AIOFile
from async_timeout import timeout
from discord.ext import commands
from discord.opus import load_opus
from pathvalidate import sanitize_filename
from youtube_dl import YoutubeDL

from ..config import (DOWNLOADS_DIR, FFMPEG_LOGLEVEL, SOUND_DIR,
                      SOUND_SUB_DIRS, SOUNDLIST_FILE_LIMIT, TTS_DIR, YTDL_DIR)
from ..utils.checks import admins_only, trusted
from ..utils.converters import SoundURLConverter, URLConverter
from ..utils.exceptions import (CommandError, InvalidVoiceChannel,
                                VoiceConnectionError)
from ..utils.filetypes import check_file_audio
from ..utils.messaging import ask_user_yes_no
from ..utils.parsing import split_text_numbers
from ..utils.sound import convert, join_wavs
from ..utils.spotify import get_spotify_song_info
from ..utils.youtube import youtube_get_top_result
from .base_cog import BaseCog

ytdlopts = {
    "format": "bestaudio/best",
    "outtmpl": f"{YTDL_DIR}/%(title)s.%(ext)s",
    "noplaylist": True,
    "nocheckcertificate": True,
    "ignoreerrors": False,
    "logtostderr": True,
    "quiet": False,
    "no_warnings": False,
    "default_search": "auto",
    "source_address": "0.0.0.0"  # ipv6 addresses cause issues sometimes
}

ffmpegopts = {
    "before_options": "-nostdin -reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -strict experimental",
    "options": f"-vn -loglevel {FFMPEG_LOGLEVEL}"
}

ytdl = YoutubeDL(ytdlopts)

VALID_FILE_TYPES = [".mp3", ".mp4", ".webm", ".wav"] # this is probably useless
FILETYPES = {".mp3", ".wav", ".m4a", ".webm", ".mp4"}


def get_file_path(directory: str, filename: str) -> Path:
    """Resolves a filename and directory, returns a Path."""
    try:
        path = list(Path(directory).glob(glob.escape(filename)+".*"))[0]
    except IndexError:
        raise ValueError("File does not exist!")
    return path


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
    async def create_source(cls, ctx: commands.Context, search: str, *, loop: asyncio.AbstractEventLoop, download=False):
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
    async def create_local_source(cls, ctx: commands.Context, subdir: str, filename: str):
        path = get_file_path(subdir, filename)

        # Send add-to-queue confirmation
        await ctx.send(f"```\nAdded {filename} to the Queue.\n```", delete_after=10)

        return cls(discord.FFmpegPCMAudio(str(path)), data={"title":filename}, requester=ctx.author)

    @classmethod
    async def regather_stream(cls, data, *, loop):
        """Used for preparing a stream, instead of downloading.

        Since Youtube Streaming links expire."""
        loop = loop or asyncio.get_event_loop()
        requester = data["requester"]

        to_run = partial(ytdl.extract_info, url=data["webpage_url"], download=False)
        data = await loop.run_in_executor(None, to_run)
        
        return cls(discord.FFmpegPCMAudio(data["url"], **ffmpegopts), data=data, requester=requester)


class AudioPlayer:
    def __init__(self, ctx):
        self.bot = ctx.bot
        self.guild = ctx.guild
        self.channel = ctx.channel
        
        if not ctx.cog or ctx.cog.qualified_name != "SoundCog":
            self.cog = self.bot.get_cog("SoundCog")
        else:
            self.cog = ctx.cog

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
                if not self.guild.voice_client or self.queue.empty() and not self.guild.voice_client.is_playing():
                    return self.destroy(self.guild)
                else:
                    continue

            if not isinstance(source, YTDLSource):
                try:
                    source = await YTDLSource.regather_stream(source, loop=self.bot.loop)
                except:
                    await self.channel.send("There was an error processing your song")
                    continue
            
            # Exit loop if AudioPlayer is destroyed while playing audio
            if not self.guild.voice_client:
                break
            
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
                 directory: str, 
                 header: str, 
                 aliases: list, 
                 path: str, 
                 color: Optional[Union[str, int]]=None) -> None:
        self.directory = directory
        self.header = header # This attribute is honestly pretty terrible
        self.aliases = aliases
        self.path = path
        self.color = color
        self.cached_at = 0.0
        self._sound_list = {}
    
    @property
    def modified_at(self) -> float:
        return Path(self.path).stat().st_mtime
    
    @property
    def sound_list(self) -> list:      
        if not self._sound_list or self.cached_at != self.modified_at:
            self.cached_at = self.modified_at       
            self._sound_list = {file_.stem: self.path for file_ in 
                                Path(self.path).iterdir() 
                                if file_.suffix in VALID_FILE_TYPES}
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
                         directory=subdir.directory,
                         header=subdir.directory.upper(),
                         aliases=subdir.aliases,
                         path=subdir.path,
                         color=self.generate_hex_color_code(subdir.directory))
                         for subdir in SOUND_SUB_DIRS
                         ]
        
        # Per-guild audio players. Key: Guild ID
        self.players: Dict[int, AudioPlayer] = {}

        # Number of sounds played by guilds in the current session
        self.played_count: DefaultDict[int, int] = defaultdict(int) # Key: Guild ID. Value: n times played

    @property
    def sound_list(self) -> dict:
        """
        Dict of K: Sound file name, V: file directory
        
        NOTE
        ----
        Raises Exception if no sound files are found.
        """
        # This is a mess now
        sound_list = {}
        for sd in self.sub_dirs:
            sl = sd.sound_list
            for k in list(sl.keys()):
                if k in sound_list:
                    new_name = self.get_unique_filename(k, ext_sound_list={**sound_list, **sl})
                    self._do_rename_file(sd.path, k, new_name)
                    sound_list[new_name] = sl.pop(k)
                    print(f"{sd.path}/{k} has been renamed to {sd.path}/{new_name}")
            sound_list.update(sl)
        if not sound_list:
            raise ValueError("No local sound files exist!")
        return sound_list
    
    def _sound_list_init(self) -> None:
        pass

    async def cleanup(self, guild: discord.Guild) -> None:
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
        """Show active Audio Players."""
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
        Display sound played count for current guild.
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
                raise InvalidVoiceChannel("No channel to join. Please either specify a valid channel or join one.")

        vc = ctx.voice_client

        # If bot is restarted while connected to a voice channel, 
        # it can sometimes get "stuck" in a channel in a state where
        # any attempts to play sound is unsuccessful
        if not vc and any(self.bot.user.id == user.id for user in channel.members):
        #if not vc and self.bot.user.id in [user.id for user in channel.members]:
            await channel.connect() # Try to connect
            await ctx.invoke(self.stop) # Immediately issue !stop command, removing bot user from channel

        if vc:
            if vc.channel.id == channel.id:
                return
            try:
                await vc.move_to(channel)
            except asyncio.TimeoutError:
                raise VoiceConnectionError(f"Moving to channel: <{channel}> timed out.")
        else:
            try:
                await channel.connect()
            except asyncio.TimeoutError:
                raise VoiceConnectionError(f"Connecting to channel: <{channel}> timed out.")
        
        # Keep ffmpeg hot (seems to fix delayed sound output on initial sound file)
        subprocess.call("ffmpeg", stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    async def play_local_source(self, ctx: commands.Context, player: AudioPlayer, sound_name: str) -> None:
        """Creates audio source from local file and adds it to player queue."""
        try:
            if sound_name:
                subdir = self.sound_list[sound_name]
            else:
                # Select random sound if no argument
                sound_name = random.choice(list(self.sound_list))
                subdir = self.sound_list[sound_name]            
        # Attempt to suggest sound files with similar names if no results
        except KeyError:
            embeds = await self._do_search(sound_name, ctx)
            if embeds and len(embeds) <= len(self.sub_dirs):
                dym = "Did you mean:"  
            else:
                dym = ""
            await ctx.send(f"No sound with name **`{sound_name}`**. {dym}")
            if dym:
                for embed in embeds:
                    await ctx.send(embed=embed)
            return
        else:
            source = await YTDLSource.create_local_source(ctx, subdir, sound_name)
            await player.queue.put(source)

    async def play_ytdl_source(self, ctx: commands.Context, player: AudioPlayer, url: str) -> None:
        """Creates audio source from online source and adds it to player queue."""
        # Check if downloading is allowed
        if ctx.invoked_with == "ytdl":
            await self.check_downloads_permissions(add_msg=
                "Use **`!play`** or **`!yt`** instead.")
            download = True
        else:
            download = False
        source = await YTDLSource.create_source(ctx, url, loop=self.bot.loop, download=download)
        await player.queue.put(source)        

    async def _play(self, ctx: commands.Context, arg: str, voice_channel: commands.VoiceChannelConverter=None) -> None:
        """Play sound in message author's voice channel
        
        Parameters
        ----------
        ctx : commands.Context
            Command invocation context
        arg : `str`
            Name of local sound file or HTTP(S) URL
        voice_channel : `commands.VoiceChannelConverter`, optional
            Specific voice channel to play sound in, 
            by default uses `ctx.message.author.voice.channel`
        """
        vc = ctx.voice_client

        if not vc:
            await ctx.invoke(self.connect, channel=voice_channel)

        player = self.get_player(ctx)
        
        # Play audio from online source
        if urlparse(arg).scheme in ["http", "https"]:
            await self.play_ytdl_source(ctx, player, arg)
        else:
            await self.play_local_source(ctx, player, arg)
        
        # Increment played count for guild
        self.played_count[ctx.guild.id] += 1
    
    @commands.command(name="play", usage="<filename>")
    async def play(self, ctx: commands.Context, *args):
        """Play local sound files.
        Use `!search` to list available sounds."""
        arg = " ".join(args)
        await self._play(ctx, arg)

    @commands.command(name="yt", aliases=["ytdl", "spotify"], usage="<url>, <search query> or <Spotify URI>")
    async def yt(self, ctx: commands.Context, *args):
        """Play YouTube or Spotify content."""
        arg = " ".join(args)
        
        if "spotify" in arg:
            await ctx.send("Attempting to find song on YouTube...", delete_after=5.0)
            artist, song, album = await self.bot.loop.run_in_executor(None, get_spotify_song_info, arg)
            arg = await self.bot.loop.run_in_executor(None, youtube_get_top_result, f"{artist} {song}")
        
        elif urlparse(arg).scheme not in ["http", "https"]:
            await ctx.send(f"Searching YouTube for `{arg}`...", delete_after=5.0)
            arg = await self.bot.loop.run_in_executor(None, youtube_get_top_result, arg)

        await self._play(ctx, arg)

    @commands.command(name="rplay", usage="<channel_id>")
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

    @commands.command(name="skip")
    async def skip(self, ctx):
        """Skip the song."""
        vc = ctx.voice_client

        if not vc or not vc.is_connected():
            return await ctx.send("I am not currently playing anything!", delete_after=5)

        if vc.is_paused():
            pass
        elif not vc.is_playing():
            return

        vc.stop()
        await ctx.send(f"**`{ctx.author}`**: Skipped the song!")

    @commands.command(name="volume", aliases=["vol"])
    @admins_only()
    async def change_volume(self, ctx, *, vol: int):
        """Set player volume (1-100)"""
        vc = ctx.voice_client

        if not vc or not vc.is_connected():
            return await ctx.send("I am not currently connected to voice!", delete_after=5)

        if not 0 < vol < 101:
            return await ctx.send("Please enter a value between 1 and 100.")

        player = self.get_player(ctx)

        if vc.source:
            vc.source.volume = vol / 100

        player.volume = vol / 100
        await ctx.send(f"**`{ctx.author}`**: Set the volume to **{vol}%**")

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

        player.np = await ctx.send(f"**Now Playing:** `{vc.source.title}` "
                                   f"requested by `{vc.source.requester}`")

    @commands.command(name="destroy", aliases=["quit"])
    @admins_only()
    async def destroy_player(self, ctx) -> None:
        vc = ctx.voice_client

        if not vc or not vc.is_connected():
            return await ctx.send("I am not currently playing anything!", delete_after=20)

        await self.cleanup(ctx.guild)

    @commands.command(name="soundlist",
                      aliases=["sounds"], description="Prints a list of all sounds on the soundboard.")
    @commands.cooldown(rate=1, per=10, type=commands.BucketType.user)
    async def soundlist(self, ctx: commands.Context, category: Optional[str]=None) -> None:
        """List soundboard files.
        
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
            [f"**`{sd.directory}`**" for sd in self.sub_dirs if sd.sound_list]
            )
        
        # Raise exception if all sound directories are empty
        if not categories:
            raise AttributeError("Soundboard has no sound files!")
        
        # Prompt user to specify category if message lacks category argument
        if not category:
            await self.send_embed_message(ctx,
                                          title="Categories", 
                                          description=categories)
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
            if not await ask_user_yes_no(ctx, msg):
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

    @commands.command(name="search", usage="<query>")
    async def search(self, 
                     ctx: commands.Context, 
                     *query: str, 
                     rtn: bool=False) -> Optional[List[discord.Embed]]:
        """Search for Soundboard files."""
        
        # Join args into space-separated search query string
        query = " ".join(query)
        if not query or query.isspace():
            raise CommandError("Search query cannot be an empty string.")
        
        embeds = await self._do_search(query, ctx)
        
        # Require searches to be specific in order to avoid spamming a channel
        if len(embeds) > len(self.sub_dirs):
            n_results = sum([len(e.description.splitlines()) for e in embeds])
            raise CommandError(f"Search returned {n_results} results. A more specific search query is required.")

        # Post search results to ctx.channel
        if embeds:
            for embed in embeds:
                await ctx.send(embed=embed)
        else:
            await ctx.send("No results")
    
    async def _do_search(self, query: str, ctx: commands.Context=None) -> List[discord.Embed]:
        """Performs Soundboard file search. Returns list of Discord Embeds"""
        if not ctx:
            ctx = await self.get_command_invocation_ctx()
        
        embeds = []
        for sf in self.sub_dirs:
            _out = [sound for sound in sf.sound_list if query.lower() in sound.lower()]
            if _out:
                _out_str = "\n".join(_out)
                _rtn_embeds = await self.send_embed_message(ctx, sf.header, _out_str, color=sf.color, return_embeds=True)
                embeds.extend(_rtn_embeds)
        
        return embeds
   
    @commands.group(name="queue", usage="[subcommand]")
    async def queue(self, ctx: commands.Context) -> None:
        """Display soundboard queue."""
        vc = ctx.voice_client

        if not vc or not vc.is_connected():
            return await ctx.send("I am not currently connected to a voice channel!", delete_after=5)

        player = self.get_player(ctx)
        if player.queue.empty():
            return await ctx.send("Queue is empty!")
        
        # Invoke subcommands
        if ctx.invoked_subcommand:
            return

        upcoming = list(islice(player.queue._queue, 0, 5))

        out_msg = "\n".join(f"{idx}. **`{up['title']}`**" for idx, up in enumerate(upcoming, 1))

        await self.send_embed_message(ctx, "Queue", out_msg, color="red")

    @queue.command(name="clear")
    async def clear_queue(self, ctx: commands.Context) -> None:
        """Clear soundboard queue."""
        player = self.get_player(ctx)

        if not player:
            return
        
        n = player.queue.qsize()
        player.destroy(ctx.guild)
        
        # Grammar
        if n == 1:
            s = ""
            werewas = "was"
        else:
            s = "s"
            werewas = "were"
        
        await ctx.send(f"Cleared queue! {n} sound{s} {werewas} cleared.")

    @commands.command(name="tts",
                      aliases=["texttospeech", "text-to-speech"])
    async def texttospeech(self, ctx: commands.Context, text: str, language: str="en", filename: Optional[str]=None) -> None:
        """Create text-to-speech sound files.
        """

        # gTTS exception handling.
        # The language list has a tendency to break, which requires gTTS to be updated
        try:
            valid_langs = gtts.lang.tts_langs()
        except:
            await self.send_log(f"**URGENT**: Update gTTS. {self.AUTHOR_MENTION}")
            raise CommandError("Text-to-speech module is unavailable. Try again later.")

        # User error and help arguments
        if not text:
            return await self.send_error_msg(ctx, "Text for TTS is a required argument.")

        elif text in ["languages", "lang", "options"]:
            _langs = [
                    f"`{lang_short}`{self.EMBED_FILL_CHAR*(8-len(lang_short))}"
                    f"{lang_long}" for lang_short, lang_long in valid_langs.items()
                    ]
            langs = "\n".join(_langs)
            return await self.send_embed_message(ctx, "Code\tLanguage", langs)
            
        await ctx.trigger_typing()

        # Use first word of text if no filename
        if not filename:
            filename = text.split(" ")[0]

        filename = await self._do_create_tts_file(text, language, filename)

        await ctx.send(f"TTS audio file created: **`{filename}`**")

        # Try to play created sound file in author"s voice channel afterwards
        #with suppress(AttributeError):
        if ctx.message.author.voice:
            cmd  = self.bot.get_command("play")
            await ctx.invoke(cmd, filename)

    async def _do_create_tts_file(self, text: str, language: str, filename: str, *, directory: str=TTS_DIR, overwrite: bool=False) -> None:
        # Get tts object
        tts = gtts.gTTS(text=text, lang=language)
        
        filename = sanitize_filename(filename)

        if not overwrite:
            # Check filename uniqueness  
            filename = self.get_unique_filename(filename)
        
        # Save mp3 file
        to_run = partial(tts.save, f"{directory}/{filename}.mp3")
        await self.bot.loop.run_in_executor(None, to_run)
        
        return filename
    
    @commands.command(name="add_sound", usage="<url> or <file attachment>")
    async def add_sound(self, ctx: commands.Context, url: str=None, filename: str=None) -> None:
        """Download sound file to soundboard.
        
        Sound file URL is passed in as argument `url` or as a message attachment.
        
        Parameters
        ----------
        ctx : `commands.Context`
            Discord Context object
        url : `str`
            HTTP(s) URL of file. 
        """

        # Check if downloading is allowed
        await self.check_downloads_permissions()
        
        # Raise exception if message has no attachment and no URL was passed in
        if not ctx.message.attachments and not url:
            return await self.send_error_msg(ctx, "A file attachment or file URL is required!")

        # Use attachment URL if message has attachment
        if ctx.message.attachments:
            attachment = ctx.message.attachments[0]
            filename, url = url, attachment.url

        # Download and save sound file
        try:
            filename = await self._do_download_sound(ctx, url, filename=filename)
        
        except AttributeError:
            raise CommandError(
                "Invalid URL. Must be a direct link to a file. "
                "Example: http://example.com/file.mp3"
                )        
        
        except ValueError:
            raise CommandError(
                f"Invalid file type. Must be one of: **{FILETYPES}**"
                )
        
        else:
            await ctx.send(f"Saved file **`{filename}`**")
        
            # Play downloaded sound if command invoker is in a voice channel
            if ctx.author.voice:
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
        filename = sanitize_filename(filename)

        # Check if file extension is recognized
        if ext not in FILETYPES:
            raise CommandError("Downloaded file is of an invalid filetype.")
        
        # Attempt to download file
        sound_file = await self.download_from_url(ctx, url)

        # Check if downloaded file is actually an audio file
        if not check_file_audio(sound_file) and ext != ".mp3": # mp3 files can't always be identified by MIME type
            raise CommandError("Downloaded file does not appear to be an audio file!")
        
        filename = self.get_unique_filename(filename)
        filepath = f"{DOWNLOADS_DIR}/{filename}{ext}"             
        
        async with AIOFile(filepath, "wb") as f:
            await f.write(sound_file.getvalue())

        await self.log_file_download(ctx, url=url, filename=f"{filename}{ext}")        
        
        return filename
    
    def get_unique_filename(self, filename: str, *, ext_sound_list: dict=None) -> str:
        # Increment i until a unique filename is found
        sl = ext_sound_list if ext_sound_list else self.sound_list
        
        # Check if filename has a trailing number that can be incremented
        head, tail = split_text_numbers(filename)  
        if tail.isnumeric():
            filename = head
            start = int(tail)
        else:
            start = 0
        
        for i in count(start=start):
            # we don't need a number if first attempted filename is unique
            i = "" if i==0 else i
            fname = f"{filename}{i}"
            if fname not in sl:
                return fname

    @commands.command(name="rename")
    @admins_only()
    async def rename_sound(self, ctx: commands.Context, original: str, new: str) -> None:
        """Renames a soundboard file."""
        directory = self.sound_list.get(original)
        
        if new in self.sound_list:
            # NOTE: ask user to overwrite?
            raise CommandError(f"**`{new}`** already exists!")
        elif original == new:
            raise CommandError("New filename cannot be identical to the original filename.")
        elif not directory:
            raise CommandError(f"Cannot find **`{original}`**!")
        
        self._do_rename_file(directory, original, new)

        await ctx.send(f"Successfully renamed **`{original}`** to **`{new}`**")

    def _do_rename_file(self, directory: str, filename: str, new: str) -> None:
        path = get_file_path(directory, filename)
        
        # Remove invalid characters
        new = sanitize_filename(new)

        try:
            path.rename(f"{path.parent}/{new}{path.suffix}")
        except:
            raise CommandError("Unable to rename file!")
                    
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
            raise CommandError("A URL or attached file is required!")

    @commands.command(name="combine")
    @admins_only()
    async def join_sound_files(self, ctx: commands.Context, file_1: str, file_2: str) -> None:
        """Combine two sound files.
        
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
        files: List[Path] = []
        
        for f in [file_1, file_2]:
            for p in Path(f"{SOUND_DIR}").glob(f"*/*{f}*"):
                if p.stem == f: # NOTE: necessary?
                    files.append(p)
                    break
            else:
                raise FileNotFoundError(f"Unable to find soundfile '{f}'")

        # Make sure all files are .wav. Convert to .wav if necessary
        tempfiles = [] # Files that are temporarily converted to .wav
        for fp in list(files): # NOTE: use enumerate() instead?
            if fp.suffix == ".mp3":
                wavname = await self.bot.loop.run_in_executor(None, convert, fp, True) 
                files[files.index(fp)] = wavname
                tempfiles.append(wavname)

        # Combine .wavs
        try:
            joined = join_wavs(*files)
        except (FileNotFoundError, FileExistsError) as e:
            raise CommandError(e)
        except Exception:
            await ctx.send("ERROR: Something went wrong when attempting to join files.")
            raise
        finally:
            # Delete temporary files (if any)
            for tf in tempfiles:
                os.remove(tf)

        # Convert joined file to mp3 (why?)
        await self.bot.loop.run_in_executor(None, convert, joined, False)
        await ctx.send(f"Combined **{file_1}** & **{file_2}**! New sound: **{joined.stem}**")

        # Delete wav version of joined file
        if Path(joined).exists():
            os.remove(joined)
