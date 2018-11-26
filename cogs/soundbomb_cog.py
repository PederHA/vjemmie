from discord.ext import commands
import discord
from ext_module import ExtModule
import os
import asyncio
from random import randint
from discord import opus

class SoundBombCog():

    def __init__(self, bot: commands.Bot, folder=None, log_channel_id: int=None, tag_dict: dict={}):

        self.folder = folder
        self.bot = bot
        self.log_channel_id = log_channel_id
        self.send_log = None             # will be assigned later
        self.sound_list = SoundBombCog._load_songs(self.folder)
        self.tag_dict = tag_dict
        self.tag_dict = dict((k.lower(), v)
                             for k, v in self.tag_dict.items())  # lower all keys
        for value in self.tag_dict:     # lower all values
            self.tag_dict[value] = [name.lower()
                                    for name in self.tag_dict[value]]
        for tag in self.tag_dict.keys():  # removing invalid filenames
            self.tag_dict[tag] = [
                name for name in self.tag_dict[tag] if name in self.sound_list]
    
    @staticmethod
    def _load_songs(folder):
        """This function returns a list with all the mp3-file names in the given folder
        Args:
            folder: The folder with the mp3 files (String)
        Returns:
            sound_list: The list with file names, all lowercase and without the .mp3 (list)
        This function raises an Exception, if the folder was empty
            """
        sound_list = sorted([i[:-4].lower()
                             for i in os.listdir(folder) if '.mp3' in i])
        if not sound_list:
            raise Exception("No mp3 files in the given folder")
        return sound_list

    async def on_ready(self) -> None:
        opus.load_opus('libopus')

    @commands.command(name='sbomb',
                      description=' tags/name || Plays the sound with the first name found in the arguments.'
                                  ' If no name is found, plays a random sound which has all tags found in the aguments.'
                                  ' Ignores upper/lowercase.'
                                  ' If no tags are found or no sound with all the given tags exists'
                                  ' the sound is chosen randomly.'
                                  ' Requires you to be in a voice channel!')
    async def play(self, ctx: commands.Context, *args):
        if len(args) != 2:
            await ctx.send("Invalid command arguments. !sbomb <channel> <sound>")
        else:
            channel_id, sound_name = args
        
            try:
                channel_id = int(channel_id)
            except:
                await ctx.send("Channel ID specified is not a valid number.")
                raise Exception
            
            try:  # user must be connected to a voice channel
                voice_channel = self.bot.get_channel(channel_id)
            except AttributeError:
                await ctx.send(content='To use this command you have to be connected to a voice channel!')
                raise discord.DiscordException

            _name_cut = self.sound_list

            for arg in args:  # check if one is a name
                if arg.lower() in self.sound_list:
                    _name_cut = [arg.lower()]
                    break
            if len(_name_cut) > 1:
                for arg in args:  # if no name is found go through the tags
                    if arg.lower() in self.tag_dict.keys():
                        # update the cut
                        _name_cut = [
                            name for name in _name_cut if name in self.tag_dict[arg.lower()]]
            if len(_name_cut) == 0:  # play a random sound if the tags have no cut
                _name_cut = self.sound_list
                try:
                    await ctx.send(content='No name with all the tags given. Playing a random sound.')
                except discord.DiscordException:
                    pass
            name = _name_cut[randint(1, len(_name_cut)) - 1]


            try:
                vc = await voice_channel.connect()
            except discord.ClientException:
                await ctx.send('I am already playing in a voice channel.'
                            ' Please try again later or stop me with the stop command!')
                raise discord.DiscordException
            vc.play(discord.FFmpegPCMAudio(self.folder + '/' + name + '.mp3'),
                    after=lambda e: SoundBombCog.disconnector(vc, self.bot))
            await self.send_log('Playing: ' + name)

    @commands.command(name='stop_bomb',
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



 