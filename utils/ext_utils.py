from typing import Iterable
from discord.ext import commands

def is_int(string: str) -> bool:
    try:
        string = int(string)
    except:
        return False
    else:
        return True

async def format_output(list_of_items: Iterable[str], item_type: str) -> str:
    """
    Creates a multi-line codeblock in markdown formatting
    with an `item_type` heading and each index of the iterable
    on new lines beneath it.
    """
    output = "```"
    output += f"Available {item_type}:\n\n"
    for item in list_of_items:
        output += f"{item}\n"
    else:
        output += "```"
    return output

async def get_users_in_author_voice_channel(ctx: commands.Context) -> list:
    squad_list = []
    try:
        if ctx.message.author.voice.channel.members is not None:
            for member in ctx.message.author.voice.channel.members:
                if member.nick != None:
                    squad_list.append(member.nick)
                else:
                    squad_list.append(member.name)
    except:
        return None
    else:
        return squad_list
