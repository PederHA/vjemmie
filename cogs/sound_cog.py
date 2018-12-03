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

class SoundboardCog(BaseCog):
    """Cog for the soundboard feature"""

    def __init__(self, bot: commands.Bot, log_channel_id: int, folder=None) -> None:
        super().__init__(bot, log_channel_id)
        self.folder = folder

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
    async def play(self, ctx: commands.Context, *args) -> None:
        """This command plays the first sound name found in args, if one exists.
        If none exists, all args will be interpreted as tags. The command will create the cut, of all
        valid tag parameters and play a random file from that.
        If that list is empty/no args is formatted validly this command plays a random sound

        Args:
            ctx: The context of the command, which is mandatory in rewrite (commands.Context)
            args: Shall contain at least one filnename or multiple tags (all String)
            """
        try:  # user must be connected to a voice channel
            voice_channel = ctx.author.voice.channel
        except AttributeError:
            await ctx.send(content='To use this command you have to be connected to a voice channel!')
            raise discord.DiscordException

        arg = " ".join(args).lower()
        if arg in self.sound_list:
            sound_name = arg
        else:
            if len(args)>0:
                await ctx.send(f"Could not find sound with name {args[0]}")
                raise Exception(f"Could not find sound with name {args[0]}")
            else:
                sound_name = random.choice(self.sound_list)
       
        try:
            vc = await voice_channel.connect()
        except discord.ClientException:
            await ctx.send('I am already playing in a voice channel.'
                           ' Please try again later or stop me with the stop command!')
            raise discord.DiscordException
        vc.play(discord.FFmpegPCMAudio(self.folder + '/' + sound_name + '.mp3'),
                after=lambda e: self.disconnector(vc))
        await self.send_log('Playing: ' + sound_name)

    @commands.command(name='stop',
                      aliases=['halt'],
                      description='The bot will stop playing a sound and leave the current voice channel.'
                                  'Requires you to be in the same voice channel as the bot!')
    async def stop(self, ctx: commands.Context) -> None:
        """This function stops the bot playing a sound and makes it leave the current voice channel.
         Args:
             ctx: The context of the command, which is mandatory in rewrite (commands.Context)
             """
        for connection in self.bot.voice_clients:
            if ctx.author.voice.channel == connection.channel:
                return await connection.disconnect()

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


    def disconnector(self, voice_client: discord.VoiceClient) -> None:
        """This function is passed as the after parameter of FFmpegPCMAudio() as it does not take coroutines.
        Args:
            voice_client: The voice client that will be disconnected (discord.VoiceClient)
            bot: The bot that will terminate the voice client, which will be this very bot
            """
        coro = voice_client.disconnect()
        fut = asyncio.run_coroutine_threadsafe(coro, self.bot.loop)
        try:
            fut.result()
        except asyncio.CancelledError:
            pass

    async def name_reaction(self, name, message) -> None:
        if name == "mw2nuke":
            await message.add_reaction('\U0001F4A3')
        # Looks in spellbook for Pick Lock
        if (name == "zonodoor") or (name == "rad1"):
            await message.add_reaction(':PedoRad:237754662361628672')

    @commands.command(name="texttospeech",
                      aliases=["tts", "text-to-speech"])
    async def texttospeech(self, ctx: commands.Context, *args) -> None:
        valid_langs = gtts.lang.tts_langs()
        if len(args) == 3:
            text, language, sound_name = args
            if language in valid_langs.keys():
                tts = gtts.gTTS(text=text, lang=language)
                file_path = f"sounds/{sound_name}.mp3"
                # Check if a file with identical name already exists
                if Path(file_path).exists():
                    await ctx.send(f"A sound file with the name **{sound_name}** already exists. Choose another name!")
                else:
                    tts.save(file_path)
                    await ctx.send(f'Sound created: **{sound_name}**')

                # Play created sound file in author's voice channel afterwards
                try:
                    if ctx.message.author.voice.channel != None:
                        cmd  = self.bot.get_command('play')
                        await ctx.invoke(cmd, sound_name)
                # Suppress error if voice channel does not exist
                except AttributeError:
                    pass
            else:
                await ctx.send("Invalid language."
                               "Type `!tts help` for more information about available languages.")
        else:
            if len(args) >= 1:
                if args[0] in ["languages", "lang", "options"]:
                    output = '```Available languages:\n\n'
                    for language_long, language_short in valid_langs.items():
                        output += f"{language_long}: {language_short}\n"
                    output += "```"
                    await ctx.send(output)
                else:
                    await ctx.send("3 arguments required: "
                                "`text` "
                                "`language` "
                                "`sound_name`."
                                "\nType `!tts lang` for more information about available languages.")

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
            path, _ = res.split(".")
            print(path)
            _, _file = path.split("\\")

        try:
            if ctx.message.author.voice.channel != None:
                cmd  = self.bot.get_command('play')
                await ctx.invoke(cmd, _file)
        # Suppress error if voice channel does not exist
        except AttributeError:
            await ctx.send("Must be in a voice channel to use this command.")
        

