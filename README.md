# vjemmie
Discord bot powered by [discord.py](https://github.com/Rapptz/discord.py)

Requirements
------------
* Python >=3.7
* FFMPEG on PATH


Installing
----------

Download or clone git repo

```sh
git clone https://github.com/PederHA/vjemmie.git
cd vjemmie
pipenv install
```

The following import statements must also be removed from `cogs/__init__.py`:
```python
from cogs.pfm_memes_cog import PFMCog
from cogs.war3_cog import War3Cog
```
I'll add a plug-n-play `cogs/__init__.py ` when I can be bothered.