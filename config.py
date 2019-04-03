from dataclasses import dataclass, field
from typing import Iterable


# Database
##########
INSERT_STUFF_HERE = None

# Soundboard config
###################

@dataclass
class SoundSubdir:
    folder: str
    aliases: list = field(default_factory=list)
    
    def __post_init__(self) -> None:
        # Add directory name to aliases
        if self.aliases and self.folder not in self.aliases:
            self.aliases.append(self.folder)
        
        # Add relative path to sound subdirectory
        self.path = f"{SOUND_DIR}/{self.folder}"

# Base sound directory
SOUND_DIR = "sounds"

# Sound subdirectories
YTDL_DIR = SoundSubdir("ytdl", ["youtube", "utube", "yt"])
TTS_DIR = SoundSubdir("tts", ["text-to-speech", "texttospeech"])
GENERAL_DIR = SoundSubdir("general", ["general", "other", "normal", "uncategorized"])
DOWNLOADS_DIR = SoundSubdir("downloads", ["downloads", "dl", "downloaded", "download"])

# Dynamic list of SoundSubdir instances. Import this one!
SOUND_SUB_DIRS = [v for v in dict(locals()).values() if isinstance(v, SoundSubdir)]