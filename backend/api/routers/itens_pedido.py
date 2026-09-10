from http import HTTPStatus
from typing import Annotated

import asyncpg
from fastapi import APIRouter, Depends, HTTPException

from api.database import get_db
from api.schemas.itens_pedido_schema import ItemFilter, ItemList, ItemResponse, ItemSchema, ItemUpdate, Message

router = APIRouter(prefix='/itens_pedido', tags=['itens_pedido'])

dbConnection = Annotated[asyncpg.Connection, Depends(get_db)]


@router.post('/', response_model=ItemResponse, status_code=HTTPStatus.CREATED)
async def create_item_pedido(db: dbConnection, item_pedido: ItemSchema):

    insert = """
    INSERT INTO itens_pedido (pedido_id, produto_id, quantidade, preco_unitario, tamanho)
    VALUES ($1, $2, $3, $4, $5)
    RETURNING id, pedido_id, produto_id, quantidade, preco_unitario, tamanho
    """

    try:
        result = await db.fetchrow(
            insert,
            item_pedido.pedido_id,
            item_pedido.produto_id,
            item_pedido.quantidade,
            item_pedido.preco_unitario,
            item_pedido.tamanho,
        )
    except asyncpg.ForeignKeyViolationError:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Pedido ou produto não encontrado.',
        )

    if result is None:
        raise HTTPException(status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail='Erro ao adicionar o item')

    return dict(result) if result else {}


@router.get('/', response_model=ItemList, status_code=HTTPStatus.OK)
async def get_item_pedido(db: dbConnection, filtrar: Annotated[ItemFilter, Depends()]):
    query = 'SELECT id, pedido_id, produto_id, quantidade, preco_unitario, tamanho FROM itens_pedido WHERE 1=1'
    params = []
    params_index = 1

    if filtrar.pedido_id:
        query += f' AND pedido_id = ${params_index}'
        params.append(filtrar.pedido_id)
        params_index += 1

    query += f' OFFSET ${params_index} LIMIT ${params_index + 1}'

    params.append(filtrar.offset)
    params.append(filtrar.limit)

    result = await db.fetch(query, *params)

    itens_pedido = [dict(row) for row in result]

    return {'itens_pedido': itens_pedido}


@router.patch('/{item_pedido_id}', response_model=ItemResponse, status_code=HTTPStatus.OK)
async def atualizar_item_pedido(db: dbConnection, item_pedido_id: int, item_pedido: ItemUpdate):
    item_db = await db.fetchrow('SELECT id FROM itens_pedido WHERE id = $1', item_pedido_id)

    if not item_db:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail='Item não encontrado no pedido')

    update_data = item_pedido.model_dump(exclude_unset=True)

    if not update_data:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail='Não foi possível atualizar o item do pedido')

    set_clauses = []
    params = []
    params_index = 1

    for field, value in update_data.items():
        set_clauses.append(f'{field} = ${params_index}')
        params.append(value)
        params_index += 1

    params.append(item_pedido_id)

    set_query = ','.join(set_clauses)
    query = f"""
        UPDATE itens_pedido
        SET {set_query}
        WHERE id = ${params_index}
        RETURNING id, pedido_id, produto_id, quantidade, preco_unitario, tamanho
    """

    result = await db.fetchrow(query, *params)

    if result is None:
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail='Falha ao atualizar o  item do pedido.',
        )

    return dict(result)


@router.delete('/{item_pedido_id}', response_model=Message, status_code=HTTPStatus.OK)
async def deletar_pedido(db: dbConnection, item_pedido_id: int):
    query = await db.fetchrow('DELETE FROM itens_pedido WHERE id = $1 RETURNING id', item_pedido_id)

    if not query:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail='Item não encontrado')

    return {'message': 'Item removido com sucesso'}
