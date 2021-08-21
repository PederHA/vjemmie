from mwthesaurus import MWClient

mw: MWClient = None


def init_mw(key: str) -> None:
    global mw
    mw = MWClient(key=key)
