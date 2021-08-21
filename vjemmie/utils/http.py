"""
Module intended to abstract away the underlying networking library that is used.

If, in the future, a better alternative to httpx becomes available, only the
functions defined in this module have to be modified, as opposed to modifying
every single call to httpx in every cog.
"""
from typing import Any

import httpx
from httpx import Response


async def get(url, *args, **kwargs) -> Response:
    """Wrapper around the async httpx.get() function"""
    async with httpx.AsyncClient() as client:
        return await client.get(url, *args, **kwargs)


async def post(url, *args, **kwargs) -> Response:
    """Wrapper around the async httpx.post() function"""
    async with httpx.AsyncClient() as client:
        return await client.post(url, *args, **kwargs)


async def put(url, *args, **kwargs) -> Response:
    """Wrapper around the async httpx.put() function"""
    async with httpx.AsyncClient() as client:
        return await client.put(url, *args, **kwargs)


async def delete(url, *args, **kwargs) -> Response:
    """Wrapper around the async httpx.delete() function"""
    async with httpx.AsyncClient() as client:
        return await client.delete(url, *args, **kwargs)
