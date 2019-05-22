from discord.ext import commands
import asyncio

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
        if r in ["y", "yes", "+", "ja", "si"]:
            return True
    finally:
        return False  
