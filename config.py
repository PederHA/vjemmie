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
DISABLE_HELP = ["Admin", "Base", "Cod", "Weather", "YouTube", "War3"]


#///////////////////
# Downloads       /
#/////////////////
MAX_DL_SIZE = 25_000_000 # 25 MB

#///////////////////
# Channels       /
#/////////////////
IMAGE_CHANNEL_ID = 549649397420392567 # Upload images
LOG_CHANNEL_ID = 340921036201525248 # Log errors
DOWNLOAD_CHANNEL_ID = 563312629045788692 # Log downloads
AUTHOR_MENTION = "<@103890994440728576>" # Creates an @BOT_AUTHOR mention. Replace with own ID


#///////////////////
# Soundboard      /
#/////////////////
SOUND_DIR = "sounds" # Base sound directory
SoundSubdir.SOUND_DIR = SOUND_DIR # Don't touch this.

# Sound subdirectories
#                      Folder  Aliases
YTDL_DIR = SoundSubdir("ytdl", ["youtube", "utube", "yt"])
TTS_DIR = SoundSubdir("tts", ["text-to-speech", "texttospeech"])
GENERAL_DIR = SoundSubdir("general", ["other", "normal", "uncategorized"])
DOWNLOADS_DIR = SoundSubdir("downloads", ["dl", "downloaded", "download"])
## Add subdirectory as SoundSubdir here ##

# Dynamic list of SoundSubdir instances. Import this one!
SOUND_SUB_DIRS = [v for v in dict(locals()).values() if isinstance(v, SoundSubdir)]