from platform import uname


def in_wsl() -> bool:
    """
    Source: https://www.scivision.dev/python-detect-wsl/
    WSL is thought to be the only common Linux kernel with Microsoft in the name, per Microsoft:
    https://github.com/microsoft/WSL/issues/4071#issuecomment-496715404
    """
    return 'Microsoft' in uname().release
