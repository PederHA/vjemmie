import asyncio
import serial_asyncio
import os
from random import randint

import discord
from discord import opus
from discord.ext import commands

from ext_module import ExtModule

from pprint import pprint

boi = "not modified"

class SerialSoundboardCog:
    """
    Super early WIP for serial controlled soundboard functionality
    ====


    TODO:
    ----
    Should probably make this a subclass of the SoundboardCog Class, 
    but for now I'm just trying trying to figure out how this should all work.
    """

    def __init__(self, bot: commands.Bot, folder=None, log_channel_id: int=None, tag_dict: dict={}):
        """The constructor for the SoundboardCog class, it assigns the important variables used by the commands below
        Args:
            bot: The bot the Cog will be added to (commands.Bot)
            folder: The path to the folder with the sound files (str)
            log_channel_id: The id of the log_channel (int)
            """
        self.folder = folder
        self.bot = bot
        self.log_channel_id = log_channel_id
        self.send_log = None             # will be assigned later
        self.sound_list = SerialSoundboardCog._load_songs(self.folder)
        self.tag_dict = tag_dict
        self.tag_dict = dict((k.lower(), v) for k, v in self.tag_dict.items())  # lower all keys
        for value in self.tag_dict:     # lower all values
            self.tag_dict[value] = [name.lower() for name in self.tag_dict[value]]
        for tag in self.tag_dict.keys():  # removing invalid filenames
            self.tag_dict[tag] = [name for name in self.tag_dict[tag] if name in self.sound_list]

    async def serialconnection(self):
        loop = asyncio.get_event_loop()
        serial_coro = serial_asyncio.create_serial_connection(loop, SerialSoundboardCog.Output, 'COM6', baudrate=9600)
        value = loop.run_until_complete(asyncio.gather(serial_coro))

        loop.run_forever() 
        loop.close()

    @staticmethod
    def _load_songs(folder):
        """This function returns a list with all the mp3-file names in the given folder
        Args:
            folder: The folder with the mp3 files (String)
        Returns:
            sound_list: The list with file names, all lowercase and without the .mp3 (list)
        This function raises an Exception, if the folder was empty
            """
        sound_list = sorted([i[:-4].lower() for i in os.listdir(folder) if '.mp3' in i])
        if not sound_list:
            raise Exception("No mp3 files in the given folder")
        return sound_list

    async def on_ready(self):
        self.send_log = ExtModule.get_send_log(self)
        await self.serialconnection()


        #opus.load_opus('libopus')  # the opus library
    
    @commands.command(name='splay',
                      description=' tags/name || Plays the sound with the first name found in the arguments.'
                                  ' If no name is found, plays a random sound which has all tags found in the aguments.'
                                  ' Ignores upper/lowercase.'
                                  ' If no tags are found or no sound with all the given tags exists'
                                  ' the sound is chosen randomly.'
                                  ' Requires you to be in a voice channel!')
    
    async def splay(self, ctx: commands.Context, *args):
        """This command plays the first sound name found in args, if one exists.
        If none exists, all args will be interpreted as tags. The command will create the cut, of all
        valid tag parameters and play a random file from that.
        If that list is empty/no args is formatted validly this command plays a random sound

        Args:
            ctx: The context of the command, which is mandatory in rewrite (commands.Context)
            args: Shall contain at least one filnename or multiple tags (all String)
            """
        try:  # user must be connected to a voice channel
            #voice_channel = ctx.author.voice.channel
            print(boi)
            test_voice_channel = self.bot.get_channel(340921036201525249)
            test_text_channel = self.bot.get_channel(340921036201525248)
            #await test_text_channel.send(str(dir(test_voice_channel.connect)))
        except AttributeError:
            #await ctx.send(content='To use this command you have to be connected to a voice channel!')
            raise discord.DiscordException

        _name_cut = self.sound_list

        for arg in args:  # check if one is a name
            if arg.lower() in self.sound_list:
                _name_cut = [arg.lower()]
                break
        if len(_name_cut) > 1:
            for arg in args:  # if no name is found go through the tags
                if arg.lower() in self.tag_dict.keys():
                    _name_cut = [name for name in _name_cut if name in self.tag_dict[arg.lower()]]  # update the cut
        if len(_name_cut) == 0:  # play a random sound if the tags have no cut
            _name_cut = self.sound_list
            try:
                await ctx.send(content='No name with all the tags given. Playing a random sound.')
            except discord.DiscordException:
                pass
        name = _name_cut[randint(1, len(_name_cut)) - 1]
        
        await SerialSoundboardCog.name_reaction(self,name,ctx.message)
            
        try:
            vc = await test_voice_channel.connect()
        except discord.ClientException:
            await ctx.send('I am already playing in a voice channel.'
                           ' Please try again later or stop me with the stop command!')
            raise discord.DiscordException
        vc.play(discord.FFmpegPCMAudio(self.folder + '/' + name + '.mp3'),
                after=lambda e: SerialSoundboardCog.disconnector(vc, self.bot))
        await self.send_log('Playing: ' + name)

    @commands.command(name='sstop',
                      aliases=['shalt'],
                      description='The bot will stop playing a sound and leave the current voice channel.'
                                  'Requires you to be in the same voice channel as the bot!')
    
    async def stop(self, ctx: commands.Context):
        """This function stops the bot playing a sound and makes it leave the current voice channel.
         Args:
             ctx: The context of the command, which is mandatory in rewrite (commands.Context)
             """
        for connection in self.bot.voice_clients:
            if ctx.author.voice.channel == connection.channel:
                return await connection.disconnect()
    
    @commands.command(name='ssoundlist',
                      aliases=['ssounds'], description='Prints a list of all sounds on the soundboard.')
    
    async def soundlist(self, ctx: commands.Context):
        """This function prints a list of all the sounds on the Soundboard to the channel/user where it was requested.
        Args:
            ctx: The context of the command, which is mandatory in rewrite (commands.Context)
            """
        _sound_string = 'List of all sounds (command format !play [soundname]):'
        for sound in self.sound_list:
            if len(_sound_string) + 1 + len(sound) > 1800:
                await ctx.channel.send('```\n' + _sound_string + '```\n')
            _sound_string = _sound_string + '\n' + sound
        await ctx.channel.send('```\n' + _sound_string + '```\n')

    @commands.command(name='staglist',
                      aliases=['stags'], description='Prints a list of all tags with soundnames on the soundboard.')
    
    async def taglist(self, ctx: commands.Context):
        """This function prints a list of all the tags with their sounds on the Soundboard to the
         channel/user where it was requested.
        Args:
            ctx: The context of the command, which is mandatory in rewrite (commands.Context)
            """
        _tag_string = 'tag || sounds\n'
        for tag in self.tag_dict.keys():
            if len(_tag_string) > 1800:
                await ctx.channel.send('```\n' + _tag_string + '```\n')
                _tag_string = ''
            _tag_string = _tag_string + tag + ' || '
            for sound in self.tag_dict[tag]:
                _tag_string = _tag_string + sound + ' '
            _tag_string = _tag_string + '\n'
        await ctx.channel.send('```\n' + _tag_string + '```\n')

    @staticmethod
    def disconnector(voice_client: discord.VoiceClient, bot: commands.Bot):
        """This function is passed as the after parameter of FFmpegPCMAudio() as it does not take coroutines.
        Args:
            voice_client: The voice client that will be disconnected (discord.VoiceClient)
            bot: The bot that will terminate the voice client, which will be this very bot
            """
        coro = voice_client.disconnect()
        fut = asyncio.run_coroutine_threadsafe(coro, bot.loop)
        try:
            fut.result()
        except asyncio.CancelledError:
            pass
    
    async def name_reaction(self, name, message):
        if name == "mw2nuke":
            await message.add_reaction('\U0001F4A3')
        # Looks in spellbook for Pick Lock
        if (name == "zonodoor") or (name == "rad1"):
            await message.add_reaction(':PedoRad:237754662361628672')
        if name == "lairynig":
            await message.add_reaction(':Kebappa:237754301919789057')
    
    class Output(asyncio.Protocol):
        def connection_made(self, transport):
            self.transport = transport
            print('port opened', transport)
            transport.serial.rts = False
            transport.write(b'hello world\n')

        def data_received(self, data):
            self.data = data.decode()
            self.data = self.data[:-1]
            print(self.data)
            if self.data == "top right":
                #SerialSoundboardCog.splay("boi","mw2intervention")
                #print("lol")
                global boi
                boi = "heyboyz"
                return "Heyo"
            #print(data.decode())
            #self.transport.close()

        def connection_lost(self, exc):
            print('port closed')
            asyncio.get_event_loop().stop()
    
    
