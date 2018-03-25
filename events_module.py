from discord.ext import commands
import discord

class EventsModule:
    # is_member using dict instead?
    @staticmethod
    def is_travis(message):
        if message.author.id == 103890994440728576:
            return True
    
    @staticmethod
    def is_rad(message):
        if message.author.id == 133875264995328000:
            return True    