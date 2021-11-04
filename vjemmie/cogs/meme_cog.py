import random
from asyncio import coroutine
from functools import partial
from pathlib import Path
from typing import Dict, List, Optional, Union
from dataclasses import dataclass

import discord
import markovify
from aiofile import AIOFile
from discord.ext import commands
from markovify import NewlineText
from praw.models import Submission

from ..db import get_db
from ..config import MAIN_DB
from ..utils.commands import add_command
from ..utils.checks import admins_only
from ..utils.exceptions import CommandError
from ..utils.voting import vote
from .base_cog import BaseCog


@dataclass
class GoodmorningSettings:
    member_chance: float = 0.05  # Chance to pick member instead of group (0-1)
    all_chance: float = 0.0001  # Chance to list every single group
    # TODO: add more settings

    @property
    def send_all(self) -> bool:
        return self._should_send(self.all_chance)

    @property
    def send_member(self) -> bool:
        return self._should_send(self.member_chance)

    def _should_send(self, chance: float) -> bool:
        return chance > random.random()


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
        self.db = get_db(MAIN_DB)

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
            print("Failed to load 'memes/txt/verbs.txt'")
            self.verb_me_daddy.enabled = False  # Disable command
            return list()

    async def random_line_from_gptfile(
        self, path: str, encoding: str = "utf-8", **kwargs
    ) -> str:
        """Kinda primitive rn. Needs some sort of caching for bigger files."""
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
    @commands.cooldown(rate=1, per=36000.0, type=commands.BucketType.member)
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
        if guild.send_all:
            subject = (
                f"{', '.join(g[0] for g in await self.db.groups_get_all_groups())}"
            )
        elif guild.send_member:
            member = random.choice(ctx.guild.members)
            subject = member.mention
        else:
            subject = f"the {await self.db.groups_get_random_group()}"

        await self.send_text_message(
            f"Good {time_of_day} to everyone apart from {subject}", ctx
        )

    @commands.command(name="goodmorning_add")
    async def goodmorning_add(self, ctx: commands.Context, *args) -> None:
        if not args:
            raise CommandError("One or more words are required")

        # Make sure first letter is uppercase, but don't touch the rest
        words = list(args)
        if not words[0][0].isupper() and words[0] != "the":
            words[0] = words[0].capitalize()
        word = " ".join(words)

        ok = await self.db.groups_add_group(ctx.message.author, word)
        if not ok:
            raise CommandError(f"`{word}` has already been added!")
        await ctx.send(f"Added `{word}`.")

    @commands.command(name="goodmorning_remove")
    @vote(votes=2)
    async def goodmorning_remove(self, ctx: commands.Context, *args) -> None:
        word = " ".join(args)
        result = await self.db.groups_delete_group(word)
        if not result:
            raise CommandError(f"Unable to find `{word}`")
        await ctx.send(f"Deleted `{word}`")

    @commands.command(name="goodmorning_search")
    async def goodmorning_search(self, ctx: commands.Context, *args) -> None:
        query = " ".join(args)
        results = await self.db.groups_find_groups(query)
        if not results:
            return await ctx.send("0 results.")
        await self.send_embed_message(
            ctx,
            title="Results",
            description="\n".join(r[0] for r in results),
        )

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
