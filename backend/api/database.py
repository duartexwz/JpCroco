from typing import AsyncGenerator

import asyncpg
from fastapi import Request

from api.settings import settings


async def create_db_pool() -> asyncpg.Pool:  # pragma: no cover
    return await asyncpg.create_pool(
        settings.DATABASE_URL,  # type: ignore
        min_size=1,
        max_size=1,
    )


async def get_db(request: Request) -> AsyncGenerator[asyncpg.Connection, None]:  # pragma: no cover
    async with request.app.state.pool.acquire() as connection:
        yield connection
