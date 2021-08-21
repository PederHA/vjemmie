from functools import partial
from typing import Dict, List

from discord.ext.commands import Bot, Context
from googleapiclient.discovery import Resource, build

from ..botsecrets import secrets
from ..config import config


def _get_youtube_client(
    api_service_name: str, api_version: str, developer_key: str
) -> Resource:
    """Initializes a YouTube API client.
    Raises `googleapiclient.errors.HttpError` if client fails to build.
    """
    return build(
        api_service_name,
        api_version,
        developerKey=developer_key,
    )


class YouTubeClient:
    def __init__(
        self, bot: Bot, api_service_name: str, api_version: str, developer_key: str
    ) -> None:
        self.bot = bot
        self.bot.loop.create_task
        self.client = _get_youtube_client(
            api_service_name,
            api_version,
            developer_key,
        )

    async def search(self, query: str, *, max_results: int = 50) -> List[dict]:
        def func() -> dict:
            return (
                self.client.search()
                .list(q=query, part="id,snippet", maxResults=max_results)
                .execute()
            )

        results = await self.bot.loop.run_in_executor(None, func)

        videos: List[dict] = []
        for search_result in results.get("items", []):
            if search_result["id"]["kind"] == "youtube#video":
                videos.append(search_result)

        if not videos:
            raise AttributeError("No videos found!")

        return videos

    async def get_top_result(self, query: str):
        results = await self.search(query)
        return config.YOUTUBE_VIDEO_URL.format(id=results[0]["id"]["videoId"])


_clients: Dict[int, YouTubeClient] = {}


async def get_youtube_client(ctx: Context) -> YouTubeClient:
    client = _clients.get(ctx.guild.id)
    if not client:
        to_run = partial(
            YouTubeClient,
            ctx.bot,
            config.YOUTUBE_API_SERVICE_NAME,
            config.YOUTUBE_API_VERSION,
            secrets.YOUTUBE_API_KEY,
        )
        client = await ctx.bot.loop.run_in_executor(None, to_run)  # type: YouTubeClient
        _clients[ctx.guild.id] = client
    return client
