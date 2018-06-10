import asyncio
import serial_asyncio
import os
import random
from random import randint
import numpy
import traceback

import discord
from discord import opus
from discord.ext import commands

from ext_module import ExtModule

from cogs.sound_cog import SoundboardCog


class SerialSoundboardCog:
    """
    Serial controlled soundboard.
    Lots of globals. Yes.
    """

    bot_global = ""
    sound_folder = ""
    sound_list = ""
    shitposting_channel = ""

    def __init__(
        self,
        bot: commands.Bot,
        folder=None,
        log_channel_id: int = None,
        tag_dict: dict = {},
    ):
        global bot_global
        global sound_folder
        global sound_list
        global shitposting_channel

        self.folder = folder
        self.bot = bot
        self.log_channel_id = log_channel_id
        self.send_log = None  # will be assigned later
        self.sound_list = SoundboardCog._load_songs(self.folder)
        self.tag_dict = tag_dict
        self.tag_dict = dict(
            (k.lower(), v) for k, v in self.tag_dict.items()
        )  # lower all keys
        for value in self.tag_dict:  # lower all values
            self.tag_dict[value] = [name.lower() for name in self.tag_dict[value]]
        for tag in self.tag_dict.keys():  # removing invalid filenames
            self.tag_dict[tag] = [
                name for name in self.tag_dict[tag] if name in self.sound_list
            ]

        bot_global = bot
        sound_folder = folder
        sound_list = self.sound_list
        shitposting_channel = 348610981204590593

    async def serialconnection(self):
        try:
            loop = asyncio.get_event_loop()
            serial_coro = serial_asyncio.create_serial_connection(
                loop, self.Output, "COM10", baudrate=9600
            )
            loop.run_until_complete(asyncio.gather(serial_coro))
            loop.run_forever()
            loop.close()
        except:
            pass

    async def on_ready(self):
        self.send_log = ExtModule.get_send_log(self)
        await self.serialconnection()

    @staticmethod
    async def async_print(value):
        global bot_global
        global shitposting_channel

        test_text_channel = bot_global.get_channel(shitposting_channel)
        await test_text_channel.send(value)

    @staticmethod
    async def serial_play(args):

        global bot_global
        global sound_folder
        global sound_list

        guild = bot_global.get_guild(133332608296681472)
        for voice_channel in guild.voice_channels:
            for member in voice_channel.members:
                if member.id == 103890994440728576:
                    user_voice_channel = voice_channel.id

        try:
            test_voice_channel = bot_global.get_channel(user_voice_channel)
        except AttributeError:
            raise discord.DiscordException

        try:
            vc = await test_voice_channel.connect()
        except discord.ClientException:
            raise discord.DiscordException

        vc.play(
            discord.FFmpegPCMAudio(sound_folder + "/" + args + ".mp3"),
            after=lambda e: SoundboardCog.disconnector(vc, bot_global),
        )

    class Output(asyncio.Protocol):
        def __init__(self):
            self.loop = asyncio.get_event_loop()

        def connection_made(self, transport):
            self.transport = transport
            print("port opened", transport)
            transport.serial.rts = False
            transport.write(b"hello world\n")

        def data_received(self, data):
            serial_data = data.decode()
            serial_data = serial_data[:-1]
            serial_data = serial_data
            try:
                if serial_data == "top left":
                    try:
                        self.loop.run_until_complete(
                            SerialSoundboardCog.serial_play("mw2nexttime")
                        )
                        self.loop.stop()
                    except:
                        pass
                elif serial_data == "top middle":
                    try:
                        self.loop.run_until_complete(
                            SerialSoundboardCog.serial_play("noice")
                        )
                    except:
                        pass
                elif serial_data == "top right":
                    try:
                        self.loop.run_until_complete(
                            SerialSoundboardCog.serial_play("rod")
                        )
                    except:
                        pass
                elif serial_data == "bottom left":
                    try:
                        crate_text = self.crate(("2"))
                        self.loop.run_until_complete(
                            SerialSoundboardCog.async_print(crate_text)
                        )
                    except:
                        pass
                elif serial_data == "bottom middle":
                    try:
                        crate_text = self.crate(("3"))
                        self.loop.run_until_complete(
                            SerialSoundboardCog.async_print(crate_text)
                        )
                    except:
                        pass
                elif serial_data == "bottom right":
                    try:
                        crate_text = self.crate(())
                        self.loop.run_until_complete(
                            SerialSoundboardCog.async_print(crate_text)
                        )
                    except:
                        pass
            except:
                error = traceback.format_exc()
                print(error)

        def connection_lost(self, exc):
            print("port closed")
            asyncio.get_event_loop().stop()

        def crate(self, args):
            if (args == ()) or (len(args) == 1 and args[0] == "m249"):
                squad = ("simon", "hugo", "travis", "steve")
            elif args[0] == "2":
                squad = ("1", "2")
            elif args[0] == "3":
                squad = ("1", "2", "3")
            elif args[0] == "4":
                squad = ("1", "2", "3", "4")
            else:
                squad = args

            # Create a list from the *args tuple, to make it mutable.
            squad = list(squad)

            # Determines size of squad and distributes guns accordingly.
            # Returns size of squad and gun list containing n=squadsize lists.
            gunsplit, armorsplit = self.roll_guns(squad)
            output = self.generate_crate_text(squad, gunsplit, armorsplit)

            return output

        def roll_guns(self, squad):
            _CRATEGUNS_ALL = [
                "AWM",
                "AUG",
                "Groza",
                "MK14",
                "Ghillie",
                "Helm",
                "Vest",
                "M249",
            ]
            GUNS = _CRATEGUNS_ALL[:4]
            EQUIPMENT = _CRATEGUNS_ALL[4:]

            # Shuffle lists
            random.shuffle(squad)
            random.shuffle(GUNS)
            random.shuffle(EQUIPMENT)

            # Divide lists by len(squad)
            squadsize = len(squad)

            gunsplit = numpy.array_split(GUNS, squadsize)
            armorsplit = numpy.array_split(EQUIPMENT, squadsize)

            # Reroll if one of the gunsplit indices is ["M249"] or ["Ghillie"]

            return gunsplit, armorsplit

        def generate_crate_text(self, squad, gunsplit, armorsplit):
            squadsize = len(squad)
            # Generate discord bot output
            output = "```"
            for n in range(squadsize):
                squad_member = str(squad[n])[0:].capitalize()
                gun = str(gunsplit[n])[1:-1].replace("'", "")
                equipment = str(armorsplit[n])[1:-1].replace("'", "")
                text_line = ""
                text_line = f"{squad_member}: " f"{gun} " f"{equipment}\n"
                output += text_line
            output += "```"
            return output
