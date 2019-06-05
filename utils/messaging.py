from discord.ext import commands
import asyncio
from config import YES_ARGS

async def confirm_yes(bot: commands.Bot, ctx: commands.Context, msg: str) -> bool:
    await ctx.send(f"{msg} [y/n]")
    def pred(m) -> bool:
        return m.author == ctx.message.author and m.channel == ctx.message.channel
    try:
        reply = await bot.wait_for("message", check=pred, timeout=10.0)
    except asyncio.TimeoutError:
        pass
    else:
        r = reply.content.lower()
        if r in YES_ARGS:
            return True 
    return False


async def wait_for_user_reply(ctx: commands.Context,
                              msg: str, 
                              *,
                              options: list=None,
                              timeout: float=10.0,
                              timeout_msg: str=None) -> bool:
    if not options:
        options = YES_ARGS
    
    if not timeout_msg:
        timeout_msg = "User did not reply in time."
    
    await ctx.send(f"{msg} **[{options[0]}/n]**") # we never actually check for "n" answer
    
    def pred(m) -> bool:
        return m.author == ctx.message.author and m.channel == ctx.message.channel
    try:
        reply = await ctx.bot.wait_for("message", check=pred, timeout=timeout)
    except asyncio.TimeoutError:
        await ctx.send(timeout_msg)
    else:
        r = reply.content.lower()
        if r in options:
            return True
    return False
