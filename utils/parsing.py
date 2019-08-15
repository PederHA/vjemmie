import re


def is_valid_command_name(command: str, search=re.compile(r'[^a-z0-9_]').search) -> bool:
    return not bool(search(command))


def split_text_numbers(text: str):
    head = text.rstrip("0123456789")
    tail = text[len(head):]
    return head, tail