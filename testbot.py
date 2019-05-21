from bot import main
from botsecrets import DEV_BOT_TOKEN
from tests.test_cog import TestCog
from cogs import COGS


if __name__ == "__main__":
    print("Dev mode active")
    test_cogs = [TestCog]
    main(DEV_BOT_TOKEN, COGS + test_cogs)