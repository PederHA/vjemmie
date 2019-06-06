import re

def is_valid_command_name(command: str, search=re.compile(r'[^a-z0-9.]').search) -> bool:
    return not bool(search(command))