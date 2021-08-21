import random
from dataclasses import dataclass
from enum import Enum, auto
from functools import partial
from pathlib import Path
from typing import Dict, List, Optional

import markovify
from aiofile import AIOFile
from discord.ext import commands
from loguru import logger
from markovify import NewlineText
from praw.models import Submission

from ..db import db
from ..utils.checks import admins_only
from ..utils.commands import add_command
from ..utils.exceptions import CommandError
from .base_cog import BaseCog


class _GoodmorningSendType(Enum):
    ALL = auto()
    MEMBER = auto()
    SINGLE = auto()


@dataclass
class GoodmorningSettings:
    member_chance: float = 0.05  # Chance to pick member instead of group (0-1)
    all_chance: float = 0.0025  # Chance to list every single group
    # TODO: add more settings

    def get_send_type(self) -> _GoodmorningSendType:
        n = random.random()
        if self.all_chance > n:
            return _GoodmorningSendType.ALL
        elif self.member_chance > n:
            return _GoodmorningSendType.MEMBER
        else:
            return _GoodmorningSendType.SINGLE


async def gpt_command(
    cls: commands.Cog,
    ctx: commands.Context,
    *,
    path: str = None,
    n_lines: Optional[int] = None,
) -> None:
    if not path:
        raise ValueError("No path lol")

    if not n_lines:
        line = await cls.random_line_from_gptfile(path)
        await ctx.send(line)
    else:
        lines = "".join(
            [await cls.random_line_from_gptfile(path) for n in range(n_lines)]
        )
        await cls.send_text_message(lines, ctx)


class MemeCog(BaseCog):
    """Text meme commands"""

    EMOJI = ":spaghetti:"

    def __init__(self, bot) -> None:
        super().__init__(bot)
        self.experimental = False
        self.wordlist: List[str] = []
        self.models: Dict[str, NewlineText] = {}
        self.daddy_verbs = self.load_daddy_verbs()
        self.files: Dict[str, List[str]] = {}

        # Per-guild goodmorning command settings (TODO: make persistent)
        self.goodmorning_settings: Dict[int, GoodmorningSettings] = {}

        self.create_gpt_commands()

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        await self._setup_goodmorning()

    async def _setup_goodmorning(self) -> None:
        for guild in self.bot.guilds:
            self.goodmorning_settings[guild.id] = GoodmorningSettings()

    def create_gpt_commands(self) -> None:
        p = Path("memes/txt/gpt")
        if not p.exists():
            return

        for file_ in p.iterdir():
            if file_.suffix != ".txt":
                continue

            add_command(
                self,
                gpt_command,
                name=file_.stem,
                group=self.gpt,
                path=str(file_),  # command kwargs
                n_lines=10,
            )

    def load_daddy_verbs(self) -> List[str]:
        """NOTE: Blocking!"""
        try:
            with open("memes/txt/verbs.txt", "r", encoding="utf-8") as f:
                return f.read().splitlines()
        except:
            logger.error("Failed to load 'memes/txt/verbs.txt'")
            self.verb_me_daddy.enabled = False  # Disable command
            return list()

    async def random_line_from_gptfile(
        self, path: str, encoding: str = "utf-8", **kwargs
    ) -> str:
        if path not in self.files:
            async with AIOFile(path, "r", encoding=encoding, **kwargs) as f:
                self.files[path] = (await f.read()).split("====================")
        return random.choice(self.files[path])

    @commands.group(name="gpt")
    async def gpt(self, ctx: commands.Context) -> None:
        if not ctx.invoked_subcommand:
            await ctx.invoke(self.bot.get_command("help"), "gpt")

    @commands.command(name="goodshit")
    async def goodshit(self, ctx: commands.Context) -> None:
        """👌👀👌👀👌👀👌👀👌👀"""
        await self.read_send_file(ctx, "memes/txt/goodshit.txt")

    @commands.command(name="mason")
    async def mason(self, ctx: commands.Context) -> None:
        "DOTA ALL STAR..."
        await self.read_send_file(ctx, "memes/txt/mason.txt")

    @commands.command(name="madara")
    async def madara(self, ctx: commands.Context) -> None:
        """Is there a character..."""
        await self.read_send_file(ctx, "memes/txt/madara.txt")

    @commands.command(name="goodmorning")
    # @commands.cooldown(rate=1, per=36000.0, type=commands.BucketType.member)
    async def goodmorning(self, ctx: commands.Context) -> None:
        await self._do_post_goodmorning(ctx, "morning")

    @commands.command(name="goodnight")
    @commands.cooldown(rate=1, per=36000.0, type=commands.BucketType.member)
    async def goodnight(self, ctx: commands.Context) -> None:
        await self._do_post_goodmorning(ctx, "night")

    async def _do_post_goodmorning(
        self, ctx: commands.Context, time_of_day: str
    ) -> None:
        # n% chance to pick a member instead of a group
        if not self.goodmorning_settings.get(ctx.guild.id, None):
            self.goodmorning_settings[ctx.guild.id] = GoodmorningSettings()

        guild = self.goodmorning_settings[ctx.guild.id]
        send = guild.get_send_type()
        if send == send.ALL:
            target = f"the {', '.join(t.target for t in await db.goodmorning_get_all_targets())}"
        elif send == send.MEMBER:
            member = random.choice(ctx.guild.members)
            target = member.mention
        else:
            t = await db.goodmorning_get_random_target()
            target = f"the {t.target}"

        await self.send_text_message(
            f"Good {time_of_day} to everyone apart from {target}", ctx
        )

    @commands.command(name="goodmorning_add")
    async def goodmorning_add(self, ctx: commands.Context, *args) -> None:
        if not args:
            raise CommandError("One or more words are required")

        # Make sure first letter is uppercase, but don't touch the rest
        words = list(args)
        if not words[0][0].isupper():
            words[0] = words[0].capitalize()
        word = " ".join(words)

        ok = await db.goodmorning_add_target(ctx.message.author, word)
        if not ok:
            raise CommandError(f"`{word}` has already been added!")
        await ctx.send(f"Added `{word}`.")

    # TODO: rename this awful command
    @commands.command(name="goodmorning_chance")
    @admins_only()
    async def goodmorning_chance(self, ctx: commands.Context, chance: int) -> None:
        """Change the % chance of picking a member."""
        if not ctx.guild:
            return await ctx.send("This command is not supported in DMs.")
        if chance < 1 or chance > 100:
            raise CommandError("Percent chance must be between 1 and 100.")
        self.goodmorning_settings[ctx.guild.id].member_chance = chance / 100
        await ctx.send(
            f"Chance to pick a member for `{self.bot.command_prefix}goodmorning` set to {chance}%"
        )

    @commands.command(name="daddy")
    async def verb_me_daddy(self, ctx: commands.Context) -> None:
        verb = random.choice(self.daddy_verbs).capitalize()
        await ctx.send(f"{verb} me daddy")

    @commands.command(name="emojipastam")
    async def emojipasta_markovchain(self, ctx: commands.Context) -> None:
        await ctx.invoke(self.markovchain_subreddit, "emojipasta")

    @commands.command(name="markovreddit", aliases=["mr"])
    async def markovchain_subreddit(
        self, ctx: commands.Context, subreddit: str
    ) -> None:
        subreddit = subreddit.lower()
        if subreddit not in self.models:
            async with ctx.typing():
                reddit_cog = self.bot.get_cog("RedditCog")
                posts = await reddit_cog._fetch_subreddit_posts(
                    subreddit, sorting="top", time="all", post_limit=1000
                )
                try:
                    await self._generate_markovchain_subreddit_model(subreddit, posts)
                except ValueError as e:
                    raise CommandError(e)

        model = self.models[subreddit]

        to_run = partial(model.make_sentence, tries=300)
        sentence = await self.bot.loop.run_in_executor(None, to_run)
        if not sentence:
            raise CommandError(f"Unable to generate a sentence for `r/{subreddit}`")

        await self.send_text_message(sentence, ctx)

    async def _generate_markovchain_subreddit_model(
        self, subreddit: str, posts: List[Submission]
    ) -> NewlineText:
        reddit_cog = self.bot.get_cog("RedditCog")
        # TODO: Check if RedditCog is disabled
        text = "\n".join([post.selftext for post in posts if post.selftext])
        if not text:
            raise ValueError("Unable to find text submissions")

        model = markovify.NewlineText(text)
        self.models[subreddit] = model
        return model

    @commands.command(name="ricardo")
    async def ricardo(self, ctx: commands.Context, limit: int = 4176) -> None:
        """Get random submission from ricardodb.tk.

        Limit is hard-coded right now because parsing the content on the site
        is a bit of a pain, and additionally their SSL certificate is not recognized
        by the `certifi` module."""
        n = random.randint(1, limit)
        await ctx.send(f"https://ricardodb.tk/post/{n}")
