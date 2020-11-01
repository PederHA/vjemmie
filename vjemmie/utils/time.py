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
