# vjemmie
Discord bot powered by [discord.py](https://github.com/Rapptz/discord.py)

Requirements
------------
* Python >=3.7
* FFmpeg on PATH
* Opus (GNU/Linux only)

    | Distro        | Command                |
    | ------------- | :-----------------     |
    | Debian/Ubuntu | `apt install libopus0` |
    | Alpine        | `apk add opus`         |


Installing
----------

1. Download or clone git repo

```sh
git clone https://github.com/PederHA/vjemmie.git
cd vjemmie
pipenv install
```

2.  Rename `botsecrets_example.py` to `botsecrets.py` and add credentials.

3. Configure channel IDs, user IDs, and directories in `config.py`

4. Run `bot.py` to start the bot.