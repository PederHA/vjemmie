from discord.ext import commands
import discord

class EventsModule:
    # Consolidate all these methods to avoid clutter?
    @staticmethod
    def is_travis(message):
        if message.author.id == 103890994440728576:
            return True
    
    @staticmethod
    def is_hoob(message):
        if message.author.id == 133908820815642624:
            return True
    
    @staticmethod
    def is_huya(message):
        if message.author.id == 133697550623571969:
            return True
    
    @staticmethod
    def is_rad(message):
        if message.author.id == 133875264995328000:
            return True
    
    @staticmethod
    def contains_rad(content):
        if "rad" in content:
            return True
