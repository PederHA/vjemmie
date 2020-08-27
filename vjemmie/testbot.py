from .bot import run
import botsecrets


def devrun():
    print("Dev mode active")
    run(botsecrets, test=True)


if __name__ == "__main__":
    devrun()
