import time
from datetime import datetime
from functools import partial
import re
from typing import Iterator, Optional, Dict
from dataclasses import dataclass, field, asdict
import json

import discord
import requests
import websockets
from aiohttp import web
from discord.ext import commands
from websockets.server import WebSocketServerProtocol

from .base_cog import BaseCog, EmbedField
from ..utils.checks import owners_only
from ..utils.exceptions import CommandError
from ..utils.experimental import get_ctx


@dataclass
class Emoji:
    name: str
    id: Optional[int] = None
    count: int = 0


@dataclass
class User:
    id: int
    total_reacts: int = 0
    reacts: Dict[int, Emoji] = field(default_factory=dict)

    @classmethod
    def fromdict(cls, d: dict) -> object:
        obj = cls.__new__(cls)
        obj.id = d["id"]
        obj.total_reacts = d["total_reacts"]
        obj.reacts = {}
        for emoji_id, data in d["reacts"].items():
            obj.reacts[int(emoji_id)] = Emoji(
                name=data["name"],
                id=data["id"],
                count=data["count"],
            )
        obj.sort_reacts()
        return obj

    def sort_reacts(self) -> None:
        r = sorted(
            [(id, emoji) for id, emoji in self.reacts.items()], 
            key=lambda i: i[1].count, 
            reverse=True)   
        self.reacts = dict(r)  



class ExperimentalCog(BaseCog):
    """Unstable/bad/temporary commands"""

    EMOJI = ":robot:"
    def __init__(self, bot) -> None:
        super().__init__(bot)
        #self.bot.loop.run_until_complete(websockets.serve(self.handler, "localhost", 9002))

    @commands.command(name="dbg")
    @owners_only()
    async def dbg(self, ctx: commands.Context) -> None:
        """Drop into debugger for TestingCog."""
        breakpoint()
        print("yeah!")

    async def handler(self, websocket: WebSocketServerProtocol, path: str):
        cmd = await websocket.recv()

        # Is this really the way to get a cmd invocation ctx for a given channel?
        channel = self.bot.get_channel(560503336013529091)
        command = self.bot.get_command(cmd)
        ctx = await self.bot.get_context(await channel.fetch_message(channel.last_message_id))
        
        await ctx.invoke(command)
        
        await websocket.send("OK")

    
    @commands.command(name="getreacts")
    async def react_stats(self, ctx: commands.Context) -> None:
        users: Dict[int, User] = {}

        channel = self.bot.get_channel(133332608296681472)
        n_msg = 0

        # Fetching messages can throw various exceptions randomly, 
        # so we do a lazy workaround here.
        try:
            async for message in channel.history(limit=None):
                if message.reactions:
                    for reaction in message.reactions:
                        emoji = reaction.emoji
                        
                        try:
                            u = await reaction.users().flatten()
                        except:
                            continue
                        
                        for user in u:
                            if user.id not in users:
                                users[user.id] = User(id=user.id)
                            
                            # Just add to total for non-discord emojis
                            if isinstance(emoji, str):
                                users[user.id].total_reacts +=1
                                continue

                            if emoji.id not in users[user.id].reacts:
                                users[user.id].reacts[emoji.id] = Emoji(name=emoji.name, id=emoji.id)
                            users[user.id].reacts[emoji.id].count += 1
                            users[user.id].total_reacts += 1
                n_msg += 1
                if n_msg % 1000 == 0:
                    print(f"Processed {n_msg} messages.")
            else:
                print(f"Finished processing {n_msg} messages.")
        except:
            pass
        
        try:
            users = {_id: asdict(user) for _id, user in users.items()}
            to_dump = json.dumps(users, indent=4)
        except:
            raise CommandError("Failed to save message reaction statistics!")
        else:
            with open("db/reacts.json", "w", encoding="utf-8") as f:
                f.write(to_dump)


    @commands.command(name="topreacters")
    async def top_reacters(self, ctx: commands.Context) -> None:
        try:
            with open("db/reacts.json", "r", encoding="utf-8") as f:
                r = json.load(f)
        except FileNotFoundError:
            raise CommandError(
                "Bot has no message reaction statistics!\n"
                f"Run `{self.bot.command_prefix}getreacts` to fetch it."
            )
        r = sorted(
            [(id, user) for id, user in r.items()], 
            key=lambda i: i[1]["total_reacts"], 
            reverse=True)
        
        reacters = {}
        
        for reacter_id, reacter in r:
            reacters[int(reacter_id)] = User.fromdict(reacter)
        
        # Print top 5 reacters
        fields = []
        for idx, (uid, user) in enumerate(reacters.items(), start=1):
            u = self.bot.get_user(int(uid))
            if not u or not user.reacts:
                continue

            emoji = next(iter(user.reacts.values()))
            fields.append(EmbedField(
                            name=u.name, 
                            value=f"Total reacts: {user.total_reacts}\nFavorite emoji: <:{emoji.name}:{emoji.id}>"
                            )
            )
            if idx == 5:
                break

        embed = await self.get_embed(ctx, title="Top Reacters", description="_", fields=fields)
        await ctx.send(embed=embed)
