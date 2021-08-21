import os
from typing import Dict
from pathlib import Path

from discord.ext import commands

from .db import RESTClient
from .models import init_pydantic_validator

db = RESTClient(os.environ.get("API_URL"))
