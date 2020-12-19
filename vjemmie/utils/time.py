from datetime import datetime, timedelta
from enum import Enum, auto
from typing import Dict, Iterable, List, Tuple

from pytz import timezone


# I originally had a good reason to make this an Enum, but now it's kinda weird
class TimeUnit(Enum):
    HOURS = "hours"
    MINUTES = "minutes"
    SECONDS = "seconds"

TIME_UNITS: Dict[str, TimeUnit] = {
    "hours": TimeUnit.HOURS,
    "hour": TimeUnit.HOURS,
    "hr": TimeUnit.HOURS,
    "h": TimeUnit.HOURS,
    "minutes": TimeUnit.MINUTES,
    "minute": TimeUnit.MINUTES,
    "min": TimeUnit.MINUTES,
    "m": TimeUnit.MINUTES,
    "seconds": TimeUnit.SECONDS,
    "second": TimeUnit.SECONDS,
    "sec": TimeUnit.SECONDS,
    "s": TimeUnit.SECONDS,
}

def parse_time_option(*message: Iterable[str]) -> Tuple[timedelta, str]:
    """Parses a message prefixed by a time option.

    Parameters
    ----------
    message : Tuple[str]
        Message prefixed by a time option

    Returns
    -------
    Tuple[timedelta, str]
        Tuple of parsed time option as timedelta and 
        message with time option removed. 

    Raises
    ------
    ValueError
        Time option can't be parsed
    """
    message = list(message) # Ensure message is mutable


    parsed: List[str] = [] # List of parsed tokens to remove from message
    kwargs: Dict[str, int] = {} # Parsed tokens + values used to construct timedelta obj
    val = 0   # Current parsed value
    parse_val = False # Whether to look for values instead of attributes
    
    for word in message:
        if parse_val:
            td_attr = TIME_UNITS.get(word)
            if not td_attr:
                raise ValueError(f"Unrecognized token '{word}' following '{val}''")
            # Set timedelta attribute with parsed value
            kwargs[td_attr.value] = val
            parsed.append(f"{val} {word}")
            val = 0
            parse_val = False
            continue
        if word.isdigit():
            val = int(word)
            parse_val = True # got a number, 
            continue         # check if next word is a recognized time unit

    if not kwargs:
        raise ValueError("No valid options found")
        
    message = " ".join(message) # the joys of Iterable[str] :-)
    
    # Remove time options from message 
    # (very inefficient)
    for word in parsed:
        message = message.replace(word, "")
    message = message.rstrip().lstrip() # Remove leading or trailing whitespace. Could this be problematic?
    
    td = timedelta(**kwargs)
    return (td, message)

def format_time(seconds: float) -> str:
    s = ""
    seconds = round(seconds)

    hours = seconds // 3600
    if hours:
        s += f"{str(hours).rjust(2, '0')}h " # only show hours if necessary

    minutes = (seconds // 60) % 60
    if minutes or hours: # show minutes if hours are shown
        s += f"{str(minutes).rjust(2, '0')}m " 

    s += f"{str(seconds - (hours * 3600) - (minutes * 60)).rjust(2, '0')}s"
    return s


def get_now_time():
    return datetime.now(timezone("Europe/Oslo"))
