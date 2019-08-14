from dataclasses import dataclass, field
from typing import Optional

@dataclass
class SoundSubdir:
    SOUND_DIR: str = field(init=False)
    directory: str
    aliases: list = field(default_factory=list)
    
    def __post_init__(self) -> None:
        if not self.SOUND_DIR:
            raise AttributeError(
                'Set class variable "SOUND_DIR" before instantiating!')
        # Add directory name to aliases
        if self.directory not in self.aliases:
            self.aliases.append(self.directory)
        
        # Add relative path to sound subdirectory
        self.path = f"{self.SOUND_DIR}/{self.directory}"
    
    def __str__(self) -> str:
        return self.path
