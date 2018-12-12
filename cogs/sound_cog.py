from discord.ext import commands
import discord
from ext_module import ExtModule
import os
import asyncio
import random
from discord import opus
import gtts
from pathlib import Path
import youtube_dl
from cogs.base_cog import BaseCog
from collections import deque

class SoundboardCog(BaseCog):
    """Cog for the soundboard feature"""

    def __init__(self, bot: commands.Bot, log_channel_id: int, folder=None) -> None:
        super().__init__(bot, log_channel_id)
        self.is_playing = False
        self.folder = folder
        self.queue = deque([], maxlen=10)
        self.vc = None
        

    @property
    def sound_list(self) -> list:
        """
        Returns list of files in the sound folder provided on class instantiation.
        
        Returns:
            sound_list: list of file names, all lowercase and without the .mp3 file extension.
        
        Raises Exception if the folder contains no .mp3 files.
        """
        sound_list = sorted([i[:-4].lower()
                             for i in os.listdir(self.folder) if '.mp3' in i])

        if not sound_list:
            raise Exception("No mp3 files in the given folder")
        return sound_list

    async def on_ready(self) -> None:
        #self.send_log = ExtModule.get_send_log(self)
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
                await ctx.send(content='To use this command you have to be connected to a voice channel!')
                raise discord.DiscordException
        
        async def parse_sound_name(arg) -> str:
            nonlocal ctx
            if arg in self.sound_list:
                sound_name = arg
            else:
                if len(args)>0:
                    await ctx.send(f"Could not find sound with name {arg}")
                    raise Exception(f"Could not find sound with name {arg}")
                else:
                    sound_name = random.choice(self.sound_list)
            return sound_name
        
        arg = " ".join(args).lower()
        sound_name = await parse_sound_name(arg)
        self.queue.append(sound_name)
        
        if not self.is_playing:
            try:
                self.vc = await voice_channel.connect()
            except discord.ClientException:
                def_msg = ('I am already playing in a voice channel.'
                            ' Please try again later or stop me with the stop command!')   
                print("we are already connected!")   
            else:
                # THIS IS AWFUL BUT IT WORKS. YIKES.
                while(len(self.queue)) > 0:
                    _nxt = self.queue.popleft()
                    await self.play_vc(ctx, _nxt)
                    while self.is_playing:
                        # Workaround for threading issues
                        # Without this while-loop, the vc instantly disconnects.
                        await asyncio.sleep(0.25)
                else:
                    for connection in self.bot.voice_clients:
                        if ctx.author.voice.channel == connection.channel:
                            await connection.disconnect()
        else:
            await ctx.send(f"**{sound_name}** added to queue.")
    
    async def play_vc(self, ctx, sound_name) -> None:
        self.is_playing = True
        def after_playing() -> None:
            self.is_playing = False
        self.vc.play(discord.FFmpegPCMAudio(self.folder + '/' + sound_name + '.mp3'),
                            after=lambda e: after_playing())
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
        self.is_playing = False
        for connection in self.bot.voice_clients:
            if ctx.author.voice.channel == connection.channel:
                await connection.disconnect()
        else:
            self.vc = None
    
    @commands.command(name='skip',
                      aliases=["next"])
    async def skip(self, ctx: commands.Context) -> None:
        self.is_playing = False
        self.vc.stop()
        if len(self.queue) > 0:
            await self.play_next(ctx)   

    async def play_next(self, ctx: commands.Context) -> None:
        self.is_playing = False
        play_cmd = self.bot.get_command("play")
        next_sound = self.queue.popleft()
        if next_sound is not None:
            await ctx.invoke(play_cmd, next_sound)

    @commands.command(name='soundlist',
                      aliases=['sounds'], description='Prints a list of all sounds on the soundboard.')
    async def soundlist(self, ctx: commands.Context) -> None:
        """This function prints a list of all the sounds on the Soundboard to the channel/user where it was requested.
        Args:
            ctx: The context of the command, which is mandatory in rewrite (commands.Context)
            """
        
        sounds_header = 'List of all sounds (command format !play [soundname]):'
        sound_string = f"{sounds_header}\n"

        for sound in self.sound_list:
            if len(sound_string) + 1 + len(sound) > 1800:
                await ctx.send(f"```{sound_string}```\n")
                sound_string = ""
            sound_string += f"{sound}\n"
        await ctx.send(f"```{sound_string}```")

    ### UNUSED
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
        _queue = ", ".join(self.queue)
        if _queue is not "":
            await ctx.send(f"Sound files currently queued up: **{_queue}**.")
        else:
            await ctx.send("No sound files in queue.")
    
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
    async def ytdl(self, ctx: commands.Context, *args) -> None:
        if len(args)>0:
            url = args[0]
        ydl_opts = {
                'outtmpl': 'sounds/%(title)s.%(ext)s',
                'format': 'bestaudio',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3'}]
                    }
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(url=url, download=True, extra_info=ydl_opts)
            res = ydl.prepare_filename(result)
            *_path, ext = res.split(".")
            # If filename contains ".", stich string back together
            path = ".".join(_path)
            _, _file = path.split("\\")

        if ctx.message.author.voice.channel is not None:
            cmd  = self.bot.get_command('play')
            await ctx.invoke(cmd, _file)

        

