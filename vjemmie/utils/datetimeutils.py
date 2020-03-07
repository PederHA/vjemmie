from datetime import datetime, timezone
from typing import Dict, Union

import ciso8601

def format_time_difference(start: datetime, tz: timezone=None) -> Dict[str, int]:    
    diff = datetime.now(tz) - start
    
    days = diff.days
    hours, remainder = divmod(diff.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    seconds += round(diff.microseconds / 1e6)
    
    difference = {
        "days": days,
        "hours": hours,
        "minutes": minutes,
        "seconds": seconds
    }
    return difference

def format_time_difference_str(timestamp: Union[datetime, str]) -> str:
    """Name TBD"""
    # Get datetime.datetime timestamp
    if isinstance(timestamp, str):
        timestamp = ciso8601.parse_datetime(timestamp)
    
    diff = datetime.now(timezone.utc) - timestamp

    # "n {hours/minutes/seconds} ago" if <1 day difference
    if diff.days < 1:
        _last_updated = format_time_difference(timestamp, tz=timezone.utc)
        # Choose largest time unit, then break
        for k, v in _last_updated.items():
            if v < 1:
                continue
            if v == 1:
                k = k[:-1] # "1 hour" instead of "1 hours"
            last_updated = f"{v} {k} ago"
            break
        else:
            # default, in case all time dict values are 0
            last_updated = "just now" 
    
    # "yesterday" if 1 day difference
    elif diff.days == 1:
        last_updated = "yesterday"

    # "n days ago" if <=1 week difference
    elif diff.days <= 7:
        last_updated = f"{diff.days} days ago"

    # Formatted date (e.g. Thu May 02 2019) if >1 week difference
    else:
        last_updated = timestamp.strftime("%a %b %d %Y")

    return last_updated