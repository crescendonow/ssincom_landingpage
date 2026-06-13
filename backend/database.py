from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import asyncpg

from .config import Settings


class Database:
    def __init__(self) -> None:
        self._pool: asyncpg.Pool | None = None

    async def connect(self, settings: Settings) -> None:
        if not settings.database_url:
            raise RuntimeError("DATABASE_URL is required")
        dsn = settings.database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
        self._pool = await asyncpg.create_pool(dsn=dsn, min_size=1, max_size=5)

    async def disconnect(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None

    @asynccontextmanager
    async def connection(self) -> AsyncIterator[asyncpg.Connection]:
        if self._pool is None:
            raise RuntimeError("Database pool is not initialized")
        async with self._pool.acquire() as conn:
            yield conn


db = Database()
