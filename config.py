from utils.ext_models import SoundSubdir


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

# Add cogs to disable !help message for. Makes cogs "unlisted".
DISABLE_HELP = ["Admin", "Cod", "Weather", "YouTube", "War3", "Management"]


#///////////////////
# Downloads       /
#/////////////////

MAX_DL_SIZE = 25_000_000 # 25 MB
DOWNLOADS_ALLOWED = True # Enables download commands such as !ytdl and !add_sound


#///////////////////
# Channels        /
#/////////////////

# Replace all channel and user IDs
IMAGE_CHANNEL_ID = 549649397420392567 # Image rehosting channel
LOG_CHANNEL_ID = 340921036201525248 # Error logging channel
DOWNLOAD_CHANNEL_ID = 563312629045788692 # Download logging channel
AUTHOR_MENTION = "<@103890994440728576>" # Creates an @BOT_AUTHOR mention. Replace with own ID
GUILD_HISTORY_CHANNEL = 565674480660119592 # Joining/leaving guilds

#///////////////////
# Soundboard      /
#/////////////////

SOUND_DIR = "sounds" # Base sound directory
SoundSubdir.SOUND_DIR = SOUND_DIR # Don't touch this.

# Sound subdirectories
#                    Directory  Aliases
YTDL_DIR = SoundSubdir("ytdl", ["youtube", "utube", "yt"])
TTS_DIR = SoundSubdir("tts", ["text-to-speech", "texttospeech"])
GENERAL_DIR = SoundSubdir("general", ["other", "normal", "uncategorized"])
DOWNLOADS_DIR = SoundSubdir("downloads", ["dl", "downloaded", "download"])
## Add subdirectory as SoundSubdir here ##

# Dynamic list of SoundSubdir instances. Import this one!
SOUND_SUB_DIRS = [v for v in dict(locals()).values() if isinstance(v, SoundSubdir)]

#///////////////////
# Users           /
#/////////////////

# List of user IDs with highest privileges for bot commands
OWNERS = [103890994440728576]