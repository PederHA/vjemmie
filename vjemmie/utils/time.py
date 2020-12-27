from datetime import datetime, timedelta
from enum import Enum, auto
from typing import Dict, Iterable, List, NamedTuple, Tuple, Union

from pytz import timezone


# I originally had a good reason to make this an Enum, but now it's kinda weird
class TimeUnit(Enum):
    MONTHS = "months" # this is not an actual datetime.timedelta param, so we need to treat it differently
    WEEKS = "weeks"
    DAYS = "days"
    HOURS = "hours"
    MINUTES = "minutes"
    SECONDS = "seconds"

# TODO: Might just be easier to have a defaultdict[str, int] for each timedelta arg?

TIME_UNITS: Dict[str, TimeUnit] = {
    "months": TimeUnit.MONTHS,
    "month": TimeUnit.MONTHS,
    "mon": TimeUnit.MONTHS, # NOTE: could clash with a future day of week option? (monday)
    "M": TimeUnit.MONTHS,
    "weeks": TimeUnit.WEEKS,
    "week": TimeUnit.WEEKS,
    "wk": TimeUnit.WEEKS,
    "w": TimeUnit.WEEKS,
    "days": TimeUnit.DAYS,
    "day": TimeUnit.DAYS,
    "d": TimeUnit.DAYS,
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


def get_valid_time_units() -> List[str]:
    """Returns a list of valid time units."""
    return [e.value for e in TimeUnit]


async def parse_time_option(message: Iterable[str]) -> Tuple[timedelta, str]:
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
            # Try to look for a time unit after a number is found
            td_attr = TIME_UNITS.get(word)
            if not td_attr:
                parse_val = False
                continue
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
        # elif is_special_time_unit(word):
        # # e.g "tomorrow"
    if not kwargs:
        raise ValueError("No valid time options found")      

    message = " ".join(message) # the joys of Iterable[str] :-)
    
    # Remove time options from message 
    # (very inefficient, and no, we can't do message.remove(word) while it's still a list.)
    for word in parsed:
        message = message.replace(word, "")
    message = message.rstrip().lstrip() # Remove leading or trailing whitespace. NOTE: Could this be problematic?
    
    kwargs = await _process_timedelta_kwargs(kwargs)
    td = timedelta(**kwargs)
    return (td, message)


async def _process_timedelta_kwargs(kwargs: Dict[str, int]) -> Dict[str, int]:
    """Turns non-timedelta kwargs into timedelta kwargs"""
    # Months need to be converted to weeks
    months = kwargs.pop(TimeUnit.MONTHS.value, 0)
    if months > 0:
        weeks = kwargs.pop(TimeUnit.WEEKS.value, 0)
        kwargs[TimeUnit.WEEKS.value] = weeks + (months * 4)
    # NOTE: can expand this function to add more non-td arguments
    return kwargs


def format_time(seconds: Union[int, float]) -> str:
    s = []
    seconds = round(seconds)

    days = seconds // 86400
    if days:
        seconds -= days * 86400
        s.append(f"{days}d")

    hours = seconds // 3600
    if hours:
        seconds -= hours * 3600
        s.append(f"{str(hours).rjust(2, '0')}h")

    minutes = seconds // 60
    if minutes or hours: # show minutes if hours are shown
        seconds -= minutes * 60
        s.append(f"{str(minutes).rjust(2, '0')}m")

    if seconds:
        s.append(f"{str(seconds).rjust(2, '0')}s")
    
    return " ".join(s)


def get_now_time():
    return datetime.now(timezone("Europe/Oslo"))
