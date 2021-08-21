from dataclasses import dataclass, field
from functools import cached_property
from typing import Optional
from pathlib import Path


def init_base_dir(d: str) -> None:
    SoundSubdir.base_dir = Path(d)


@dataclass
class SoundSubdir:
    base_dir: Path = field(init=False)
    directory: str
    aliases: list = field(default_factory=list)

    @cached_property
    def path(self) -> Path:
        return self.base_dir / self.directory

    def __post_init__(self) -> None:
        if not self.base_dir:
            raise AttributeError(
                'Set class variable "base_dir" before instantiating!'
            )  # TODO: Remove this bullshit
        # Add directory name to aliases
        if self.directory not in self.aliases:
            self.aliases.append(self.directory)

    def __str__(self) -> str:
        return str(self.path)
