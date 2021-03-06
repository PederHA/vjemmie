from .utils.ext_models import SoundSubdir

VERSION = "0.1.0"

# DATABASE
# -----------------

# Delete this if cloning
GENERAL_DB_PATH = "pfm.db"
PFM_MEMES_DB_PATH = "memes/pfm_memes.db"
INSERT_STUFF_HERE = None
BLACKLIST_PATH = "db/blacklist.json"

# Keep
DB_DIR = "db"
MAIN_DB = f"{DB_DIR}/vjemmie.db"
TRUSTED_DIR = f"{DB_DIR}/access"
TRUSTED_PATH = f"{TRUSTED_DIR}/trusted.json"
TEMP_DIR = "temp"
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
OWNER_ID = 103890994440728576 # Replace with own User ID
AUTHOR_MENTION = f"<@{OWNER_ID}>" # Creates an @BOT_AUTHOR mention.


# SOUNDBOARD
# -----------------

# Base sound directory
SOUND_DIR = "sounds" 

# Don't touch this.
SoundSubdir.SOUND_DIR = SOUND_DIR 

# Maximum limit of sound files a directory can have before `!soundlist`
# sends its output as a DM instead of in the ctx.channel
SOUNDLIST_FILE_LIMIT = 150 

# FFMPEG Logging Level (see https://ffmpeg.org/ffmpeg.html#Generic-options)
FFMPEG_LOGLEVEL = "info"

# Sound subdirectories
#                    Directory  Aliases
YTDL_DIR = SoundSubdir("ytdl", ["youtube", "utube", "yt"])
TTS_DIR = SoundSubdir("tts", ["text-to-speech", "texttospeech"])
GENERAL_DIR = SoundSubdir("general", ["other", "normal", "uncategorized"])
DOWNLOADS_DIR = SoundSubdir("downloads", ["dl", "downloaded", "download"])
## Add subdirectory as SoundSubdir here ##

# Dynamic list of SoundSubdir instances. Import this one!
SOUND_SUB_DIRS = [v for v in dict(locals()).values() if isinstance(v, SoundSubdir)]


# ARGUMENTS
# -----------------
YES_ARGS = ["y", "yes", "+", "ja", "si", "True", "true"]
NO_ARGS = ["n", "no", "-", "nei", "False", "false"]
ALL_ARGS = ["all", "everyone", "global"]


# YouTube API
YOUTUBE_API_SERVICE_NAME = 'youtube'
YOUTUBE_API_VERSION = 'v3'
YOUTUBE_VIDEO_URL = "https://www.youtube.com/watch?v={id}"