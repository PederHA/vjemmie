import os
from dataclasses import Field, dataclass
from pathlib import Path

from .utils.ext_models import SoundSubdir, init_base_dir

VERSION = "0.1.0"

# DATABASE
# -----------------
DB_DIR = "db"
STATS_DIR = "stats"

# COGS
# -----------------

# Nothing here


# DOWNLOADS
# -----------------

# 25 MB
MAX_DL_SIZE = 25_000_000

# Enables download commands such as !ytdl and !add_sound
DOWNLOADS_ALLOWED = True


# GUILDS
# -----------------
TEST_SERVER_ID = 340921036201525248
DGVGK_SERVER_ID = 178865018031439872
PFM_SERVER_ID = 133332608296681472


# CHANNELS
# -----------------

# NOTE: If self-hosting the bot, replace all channel and user IDs with own
# Guild, Channel & User IDs

# Image rehosting
IMAGE_CHANNEL_ID = 549649397420392567

# General log
LOG_CHANNEL_ID = 340921036201525248

# Error log
ERROR_CHANNEL_ID = 604388280200593411

# File download log
DOWNLOAD_CHANNEL_ID = 563312629045788692

# Joining/leaving guilds log
GUILD_HISTORY_CHANNEL = 565674480660119592

# Channel to use as base for ctx (see BaseCog.get_command_invocation_ctx())
COMMAND_INVOCATION_CHANNEL = 584386122004561920


# USERS
# -----------------
OWNER_ID = 103890994440728576  # Replace with own User ID
AUTHOR_MENTION = f"<@{OWNER_ID}>"  # Creates an @BOT_AUTHOR mention.


# SOUNDBOARD
# -----------------

# # Base sound directory
# SOUND_DIR = "sounds"

# # Don't touch this.
# SoundSubdir.SOUND_DIR = SOUND_DIR

# Maximum limit of sound files a directory can have before `!soundlist`
# sends its output as a DM instead of in the ctx.channel
SOUNDLIST_FILE_LIMIT = 150

# FFMPEG Logging Level (see https://ffmpeg.org/ffmpeg.html#Generic-options)
FFMPEG_LOGLEVEL = "info"

# Sound subdirectories
# #                    Directory  Aliases
# YTDL_DIR = SoundSubdir("ytdl", ["youtube", "utube", "yt"])
# TTS_DIR = SoundSubdir("tts", ["text-to-speech", "texttospeech"])
# GENERAL_DIR = SoundSubdir("general", ["other", "normal", "uncategorized"])
# DOWNLOADS_DIR = SoundSubdir("downloads", ["dl", "downloaded", "download"])
# ## Add subdirectory as SoundSubdir here ##

# Dynamic list of SoundSubdir instances. Import this one!
SOUND_SUB_DIRS = [v for v in dict(locals()).values() if isinstance(v, SoundSubdir)]


from typing import Any, List, Union

ConfigValueT = Union[str, int, List[str]]


class ConfVal:
    val: ConfigValueT

    def __init__(self, val: ConfigValueT) -> None:
        self.val = val


class StringArrayVal(ConfVal):
    val: List[str]


class StringVal(ConfVal):
    val: str


class IntVal(ConfVal):
    val: int


@dataclass
class Config:
    BLACKLIST_PATH: Path = os.environ.get("BLACKLIST_PATH", "db/blacklist.json")

    TEMP_DIR: Path = os.environ.get("TEMP_DIR", "temp")
    STATS_DIR: Path = os.environ.get("STATS_DIR", "stats")

    # COGS
    # -----------------

    # Nothing here

    # DOWNLOADS
    # -----------------

    # 25 MB
    MAX_DL_SIZE: int = os.environ.get("MAX_DL_SIZE", 25_000_000)

    @property
    def MAX_DL_SIZE_FMT(self) -> str:
        return f"{self.MAX_DL_SIZE / 1_000_000 } MB"

    # Enables download commands such as !ytdl and !add_sound
    DOWNLOADS_ALLOWED: bool = os.environ.get("DOWNLOADS_ALLOWED", True)

    # GUILDS
    # -----------------

    TEST_SERVER_ID: int = os.environ.get("TEST_SERVER_ID", 340921036201525248)
    DGVGK_SERVER_ID: int = os.environ.get("DGVGK_SERVER_ID", 178865018031439872)
    PFM_SERVER_ID: int = os.environ.get("PFM_SERVER_ID", 133332608296681472)

    # CHANNELS
    # -----------------

    # NOTE: If self-hosting the bot, replace all channel and user IDs with own
    # Guild, Channel & User IDs

    # Image rehosting
    IMAGE_CHANNEL_ID: int = os.environ.get("IMAGE_CHANNEL_ID", 549649397420392567)

    # General log
    LOG_CHANNEL_ID: int = os.environ.get("LOG_CHANNEL_ID", 340921036201525248)

    # Error log
    ERROR_CHANNEL_ID: int = os.environ.get("ERROR_CHANNEL_ID", 604388280200593411)

    # File download log
    DOWNLOAD_CHANNEL_ID: int = os.environ.get("DOWNLOAD_CHANNEL_ID", 563312629045788692)

    # Joining/leaving guilds log
    GUILD_HISTORY_CHANNEL: int = os.environ.get(
        "GUILD_HISTORY_CHANNEL", 565674480660119592
    )

    # Channel to use as base for ctx (see BaseCog.get_command_invocation_ctx())
    COMMAND_INVOCATION_CHANNEL: int = os.environ.get(
        "COMMAND_INVOCATION_CHANNEL", 584386122004561920
    )

    # USERS
    # -----------------
    OWNER_ID: int = os.environ.get(
        "OWNER_ID", 103890994440728576
    )  # Replace with own User ID
    AUTHOR_MENTION: str = f"<@{OWNER_ID}>"  # Creates an @BOT_AUTHOR mention.

    # SOUNDBOARD
    # -----------------

    # Maximum limit of sound files a directory can have before `!soundlist`
    # sends its output as a DM instead of in the ctx.channel
    SOUNDLIST_FILE_LIMIT: int = os.environ.get("SOUNDLIST_FILE_LIMIT", 150)

    # FFMPEG Logging Level (see https://ffmpeg.org/ffmpeg.html#Generic-options)
    FFMPEG_LOGLEVEL: str = os.environ.get("FFMPEG_LOGLEVEL", "info")

    # Base sound directory
    SOUND_DIR: str = os.environ.get("SOUND_DIR", "sounds")

    # Don't touch this.
    init_base_dir(os.environ.get("SOUND_DIR", "sounds"))

    # Sound subdirectories
    YTDL_DIR = SoundSubdir(directory="ytdl", aliases=["youtube", "utube", "yt"])
    TTS_DIR = SoundSubdir(directory="tts", aliases=["text-to-speech", "texttospeech"])
    GENERAL_DIR = SoundSubdir(
        directory="general", aliases=["other", "normal", "uncategorized"]
    )
    DOWNLOADS_DIR = SoundSubdir(
        directory="downloads", aliases=["dl", "downloaded", "download"]
    )
    ## Add subdirectory as SoundSubdir here ##

    # Dynamic list of SoundSubdir instances. Import this one!
    SOUND_SUB_DIRS = [v for v in dict(locals()).values() if isinstance(v, SoundSubdir)]

    # ARGUMENTS
    # -----------------
    YES_ARGS = ["y", "yes", "+", "ja", "si", "True", "true"]
    NO_ARGS = ["n", "no", "-", "nei", "False", "false"]
    ALL_ARGS = ["all", "everyone", "global"]

    # YouTube API
    YOUTUBE_API_SERVICE_NAME: str = os.environ.get(
        "YOUTUBE_API_SERVICE_NAME", "youtube"
    )
    YOUTUBE_API_VERSION = os.environ.get("YOUTUBE_API_VERSION", "v3")
    YOUTUBE_VIDEO_URL = os.environ.get(
        "YOUTUBE_VIDEO_URL", "https://www.youtube.com/watch?v={id}"
    )

    def __post_init__(self) -> None:
        handlers = {
            Path: self._handle_field_path,
            bool: self._handle_field_bool,
        }

        for name, field in self.__dataclass_fields__.items():
            handler_func = handlers.get(field.type, None)
            if not handler_func:
                continue
            handler_func(name, field)

        self.create_dirs()

    def create_dirs(self) -> None:
        pass

    def _handle_field_path(self, name: str, field: Field) -> None:
        attr = getattr(self, name)
        if self._is_correct_type(attr, field):
            return attr

        try:
            a = Path(attr)
        except TypeError:
            raise TypeError(
                f"Invalid value for config value {name}. {attr} is not a valid path."
            )
        setattr(self, name, a)

    def _handle_field_bool(self, name: str, field: Field) -> None:
        attr = getattr(self, name)
        if self._is_correct_type(attr, field):
            return attr

        try:
            a = bool(attr)
        except TypeError:
            raise TypeError(
                f"Invalid value for config value {name}. {attr} can not be interpreted as a bool."
            )
        setattr(self, name, a)

    def _is_correct_type(self, attr: Any, field: Field) -> bool:
        return type(attr) == field.type


config = Config()
