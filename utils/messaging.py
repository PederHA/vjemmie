import asyncio
from collections.abc import Sequence
from itertools import chain
from typing import Any, Iterable

import discord
from discord.ext import commands

from config import YES_ARGS
from utils.exceptions import CommandError


async def get_user_reply(ctx: commands.Context,
                         *,
                         timeout: float=10.0,
                         timeout_msg: str=None) -> str:
    if not timeout_msg:
        timeout_msg = "User did not reply in time."

    def pred(m) -> bool:
        return m.author == ctx.message.author and m.channel == ctx.message.channel

    try:
        reply = await ctx.bot.wait_for("message", check=pred, timeout=timeout)
    except asyncio.TimeoutError:
        await ctx.send(timeout_msg)
        raise
    else:
        return reply.content


async def ask_user(ctx: commands.Context,
                              msg: str,
                              *options: list,
                              timeout: float=10.0,
                              timeout_msg: str=None,
                              show_no: bool=False) -> bool:
    if not options:
        options = YES_ARGS

    _opts = []
    for opt in options:
        if not isinstance(opt, Sequence):
            raise TypeError("Options must be iterable!")
        _opts.append(opt[0]) # Append first option for each category: ["yes", "y", "+"] -> "yes"
    opts_str = "/".join(_opts) # e.g. "yes/no"

    n = "/n" if show_no else ""
    await ctx.send(f"{msg} **[{opts_str}{n}]**")

    reply = await get_user_reply(ctx, timeout=timeout, timeout_msg=timeout_msg)
    
    return reply.lower() in chain.from_iterable(options)


async def ask_user_yes_no(ctx: commands.Context, msg: str) -> bool:
    return await ask_user(ctx, msg, YES_ARGS, show_no=True)


async def fetch_message(ctx: commands.Context, message_id: int) -> discord.Message:
    """Small wrapper around ctx.fetch_message() that handles common exceptions."""
    try:
        msg = await ctx.fetch_message(message_id)
    except discord.NotFound:
        raise CommandError(f"Cannot find message with ID `{message_id}`!")
    except discord.Forbidden:
        raise CommandError("Lacking permissions to fetch message!")
    except discord.HTTPException:
        raise CommandError("Failed to retrieve message. Try again later!")
    else:
        return msg
