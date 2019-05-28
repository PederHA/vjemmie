import datetime
from typing import Dict

def format_time_difference(start: datetime.datetime) -> Dict[str, int]:
    diff = datetime.datetime.now() - start
    
    days = diff.days
    hours, remainder = divmod(diff.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    seconds += round(diff.microseconds / 1e6)
    
    uptime = {
        "days": days,
        "hours": hours,
        "minutes": minutes,
        "seconds": seconds
    }
    return uptime
