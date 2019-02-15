def is_travis(message):
    return message.author.id == 103890994440728576


def is_hoob(message):
    return message.author.id == 133908820815642624


def is_huya(message):
    return message.author.id == 133697550623571969


def is_rad(message):
    return message.author.id == 133875264995328000


def contains_rad(iterable):
    return "rad" in iterable
