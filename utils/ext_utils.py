from typing import Iterable

def is_int(string: str) -> bool:
    try:
        string = int(string)
    except:
        return False
    else:
        return True

def format_output(list_of_items: Iterable[str], item_type: str) -> str:
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