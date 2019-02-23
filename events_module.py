import os
import asyncio
import json
import discord
from discord.ext import commands

def is_travis(message):
    return message.author.id == 103890994440728576


def is_hoob(message):
    return message.author.id == 133908820815642624


def is_huya(message):
    return message.author.id == 133697550623571969


def is_rad(message):
    return message.author.id == 133875264995328000


def contains_rad(iterable):
    return "rad" in iterable

async def _find_member(bot, target_member: str=None) -> None: # FIXME: rtn value
    NAMES = {
        "travis": "trvllfjvz",
        "steve": "steve",
        "jeff": "jeffrey",
        "hugo": "hugo",
        "ferdy": "ferdyg",
        "cal": "khunee",
        "calum": "khunee"
    }
    target_member = NAMES.get(target_member, "trvllfjvz")
    for member in bot.get_all_members():
        if member.name.lower() == target_member and member.voice is not None:
            return member
    else:
        raise AttributeError

async def check_alexa_dir(bot, file_name: str, debug=True) -> None: # FIXME: rtn values
    MUTE = {"mute": True}
    UNMUTE = {"mute": False}
    DEAFEN = {"deafen": True}
    UNDEAFEN = {"deafen": False}
    
    actions = {
        "mute": MUTE,
        "new": MUTE,
        "stop": MUTE,
        "unmute": UNMUTE,
        "start": UNMUTE,
        "deafen": DEAFEN,
        "deaf": DEAFEN,
        "death": DEAFEN,
        "listen": UNDEAFEN,
        "undeaf": UNDEAFEN,
        "undeafen": UNDEAFEN,
        "undeath": UNDEAFEN
    }

    file_name = f"{file_name}.json"
    baseline = os.stat(file_name)
    while True:
        statinfo = os.stat(file_name)
        if baseline != statinfo:
            with open(file_name, "r") as f:    
                alexa_out = json.load(f)
                try:
                    command, member = alexa_out
                except:
                    pass
                else:
                    action = actions.get(command)   
            # do bot stuff
            baseline = statinfo # create new baseline
            if action:
                target_member = await _find_member(bot, member)
                try:
                    await target_member.edit(**action)
                except:
                    pass    
        # sleep 1 second after every pass
        await asyncio.sleep(1)
