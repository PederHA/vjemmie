from bot import main
from botsecrets import DEV_BOT_TOKEN
from tests.test_cog import TestCog


if __name__ == "__main__":
    print("Dev mode active")
    main(DEV_BOT_TOKEN, TestCog)