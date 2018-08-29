def is_int(string: str) -> bool:
    try:
        string = int(string)
    except:
        return False
    else:
        return True

