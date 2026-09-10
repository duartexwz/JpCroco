import asyncio
from typing import Any, AsyncGenerator
from urllib.parse import urlparse

import asyncpg
from fastapi import HTTPException, Request

from api.settings import settings

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


async def get_db(request: Request) -> AsyncGenerator[asyncpg.Connection, None]:  # pragma: no cover
    """Uma conexão dedicada por requisição.

    Sem pool compartilhado de propósito: no serverless (Vercel) cada
    invocação pode rodar em um event loop diferente, e o Pool do asyncpg
    é amarrado ao loop de criação (`self._loop`) — reusá-lo entre loops
    quebra com "attached to a different loop" / "Event loop is closed".
    Com pgbouncer no caminho, abrir uma conexão por requisição é barato.
    """
    try:
        conn = await asyncpg.connect(settings.DATABASE_URL, **db_connect_kwargs())  # type: ignore
    except (OSError, asyncio.TimeoutError, asyncpg.PostgresError) as e:
        raise HTTPException(status_code=503, detail='Banco de dados indisponível') from e
    try:
        yield conn
    finally:
        await conn.close()
