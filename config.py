from utils.ext_models import SoundSubdir

VERSION = "0.1.0"

#///////////////////
# Database        /
#/////////////////

# Delete this if cloning
GENERAL_DB_PATH = "pfm.db"
PFM_MEMES_DB_PATH = "memes/pfm_memes.db"
INSERT_STUFF_HERE = None


#///////////////////
# Cogs            /
#/////////////////



#///////////////////
# Downloads       /
#/////////////////

MAX_DL_SIZE = 25_000_000 # 25 MB
DOWNLOADS_ALLOWED = True # Enables download commands such as !ytdl and !add_sound

#///////////////////
# Users           /
#/////////////////

OWNER_ID = 103890994440728576 # Replace with own User ID
AUTHOR_MENTION = f"<@{OWNER_ID}>" # Creates an @BOT_AUTHOR mention.

#///////////////////
# Channels        /
#/////////////////

# Replace all channel and user IDs
IMAGE_CHANNEL_ID = 549649397420392567 # Image rehosting channel
LOG_CHANNEL_ID = 340921036201525248 # Error logging channel
DOWNLOAD_CHANNEL_ID = 563312629045788692 # Download logging channel
GUILD_HISTORY_CHANNEL = 565674480660119592 # Joining/leaving guilds
COMMAND_INVOCATION_CHANNEL = 584386122004561920 # Channel to use as base for ctx (see BaseCog.get_command_invocation_ctx())

#///////////////////
# Soundboard      /
#/////////////////

SOUND_DIR = "sounds" # Base sound directory
SoundSubdir.SOUND_DIR = SOUND_DIR # Don't touch this.
# Maximum limit of sound files a directory can have before `!soundlist`
# sends its output as a DM instead of in the ctx.channel
SOUNDLIST_FILE_LIMIT = 150 

# Sound subdirectories
#                    Directory  Aliases
YTDL_DIR = SoundSubdir("ytdl", ["youtube", "utube", "yt"])
TTS_DIR = SoundSubdir("tts", ["text-to-speech", "texttospeech"])
GENERAL_DIR = SoundSubdir("general", ["other", "normal", "uncategorized"])
DOWNLOADS_DIR = SoundSubdir("downloads", ["dl", "downloaded", "download"])
CHERNOBYL_DIR = SoundSubdir("chernobyl", ["cherno", "ch"])

## Add subdirectory as SoundSubdir here ##

# Dynamic list of SoundSubdir instances. Import this one!
SOUND_SUB_DIRS = [v for v in dict(locals()).values() if isinstance(v, SoundSubdir)]

#///////////////////
# Arguments       /
#/////////////////
YES_ARGS = ["y", "yes", "+", "ja", "si"]
NO_ARGS = ["n", "no", "-", "nei"]
ALL_ARGS = ["all", "everyone", "global"]