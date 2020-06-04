import re
from typing import Tuple

def is_valid_command_name(command: str, search=re.compile(r'[^a-z0-9_]').search) -> bool:
    return not bool(search(command))


def split_text_numbers(text: str) -> Tuple[str, str]:
    """
    >>> split_text_numbers("foo123")
    ('foo', '123')
    """
    head = text.rstrip("0123456789")
    tail = text[len(head):]
    return head, tail