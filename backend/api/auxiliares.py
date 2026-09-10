import secrets
import string
from typing import Annotated

import asyncpg
from fastapi import Depends

from api.database import get_db

database_loja = Annotated[asyncpg.Connection, Depends(get_db)]


CHARS = string.ascii_uppercase


async def gerar_codigo(tamanho=6) -> str:
    return ''.join(secrets.choice(CHARS) for _ in range(tamanho))


async def gerar_codigo_unico(
    db: database_loja,
    tamanho: int = 6,
    max_tentativas: int = 1000,
) -> str:
    query = 'SELECT 1 FROM pedidos WHERE id_pedido = $1'

    for _ in range(max_tentativas):
        codigo = await gerar_codigo(tamanho)

        existe = await db.fetchrow(query, codigo)

        if not existe:
            return codigo
    raise RuntimeError('Não foi possível gerar um código único após várias tentativas.')
