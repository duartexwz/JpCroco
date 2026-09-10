import asyncio
import logging
from typing import Any, AsyncGenerator
from urllib.parse import urlparse

import asyncpg
from fastapi import FastAPI, Request

from api.settings import settings

log = logging.getLogger('db')

LOCAL_HOSTS = {'localhost', '127.0.0.1', '::1', 'db', 'loja_online_db', 'postgres'}


def db_connect_kwargs(url: str | None = None) -> dict[str, Any]:
    """Kwargs extras para asyncpg conforme o destino.

    - Banco remoto (ex: Neon): exige SSL (asyncpg ignora `sslmode` na URL,
      então passamos `ssl='require'` explicitamente).
    - Endpoint pooled/pgbouncer (ex: Neon `-pooler`): prepared statements
      não funcionam em transaction-pooling -> `statement_cache_size=0`.
    - Banco local (Docker): mantém o comportamento padrão (mais rápido).
    """
    target = url or settings.DATABASE_URL or ''
    host = (urlparse(target).hostname or '').lower()
    if not host or host in LOCAL_HOSTS:
        return {}
    kwargs: dict[str, Any] = {'ssl': 'require'}
    if 'pooler' in host or 'pgbouncer' in host:
        kwargs['statement_cache_size'] = 0
    return kwargs


def db_url_for_ddl() -> str:
    """URL preferida para migrações/DDL: direta quando configurada."""
    return settings.DATABASE_URL_UNPOOLED or settings.DATABASE_URL  # type: ignore


async def create_db_pool() -> asyncpg.Pool:  # pragma: no cover
    return await asyncpg.create_pool(
        settings.DATABASE_URL,  # type: ignore
        min_size=settings.DB_POOL_MIN_SIZE,
        max_size=settings.DB_POOL_MAX_SIZE,
        **db_connect_kwargs(),
    )


async def create_db_pool_resilient() -> asyncpg.Pool:
    """Cria o pool com retry: no sandbox serverless (Vercel) a rede pode
    recusar o TCP inicial (OSError EBUSY) durante o cold start."""
    last_error: Exception | None = None
    for attempt in range(1, 4):
        try:
            return await create_db_pool()
        except (OSError, asyncio.TimeoutError) as e:  # pragma: no cover
            last_error = e
            log.warning('Pool DB tentativa %s/3 falhou: %s', attempt, str(e)[:150])
            await asyncio.sleep(0.5 * attempt)
    raise last_error or RuntimeError('falha ao criar pool do banco')  # pragma: no cover


async def ensure_pool(app: FastAPI) -> asyncpg.Pool:
    """Retorna o pool compartilhado, criando sob demanda (lazy).

    Nunca derruba o startup: se a criação falhar, o erro só aparece
    quando a primeira requisição precisar do banco.
    """
    pool = getattr(app.state, 'pool', None)
    if pool is not None:
        return pool
    lock = getattr(app.state, 'pool_lock', None)
    if lock is None:
        lock = asyncio.Lock()
        app.state.pool_lock = lock
    async with lock:
        pool = getattr(app.state, 'pool', None)
        if pool is None:
            pool = await create_db_pool_resilient()
            app.state.pool = pool
    return pool


async def get_db(request: Request) -> AsyncGenerator[asyncpg.Connection, None]:  # pragma: no cover
    pool = await ensure_pool(request.app)
    async with pool.acquire() as connection:
        yield connection
