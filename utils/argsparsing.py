from utils.exceptions import EmptyArgsError, InvalidObjectType

def parse_args(args: tuple, max_length: int) -> tuple:
    if args == ():
        raise EmptyArgsError
    elif type(args) is not tuple:
        raise InvalidObjectType(f"Object 'args' is of type {type(args)}, not tuple.")
    if len(args) <= max_length:
        returned = []
        for arg in args:
            returned.append(arg)
        remaining = max_length - len(args)
        if remaining > 0:
            for n in range(remaining):
                returned.append(None)
        returned = tuple(returned)
        return returned
    else:
        return args[:max_length]
