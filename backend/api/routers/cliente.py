from http import HTTPStatus
from typing import Annotated

import asyncpg
from fastapi import APIRouter, Depends, HTTPException

from api.database import get_db
from api.schemas.clientes_schema import ClientesFilter, ClientesList, ClientesResponse, ClientesSchema, ClientesUpdate, Message
from api.security import get_current_admin, get_current_user

router = APIRouter(prefix='/clientes', tags=['clientes'])

dbConnection = Annotated[asyncpg.Connection, Depends(get_db)]
CurrentUser = Annotated[dict, Depends(get_current_user)]
CurrentAdmin = Annotated[dict, Depends(get_current_admin)]


@router.post('/', response_model=ClientesResponse, status_code=HTTPStatus.CREATED)
async def create_cliente(db: dbConnection, cliente: ClientesSchema, user: CurrentUser):
    # trata duplicidade por email e cpf (ambos UNIQUE)
    existentes = await db.fetchrow('SELECT id FROM clientes WHERE email=$1 OR cpf=$2', cliente.email, cliente.cpf)
    if existentes:
        # atualiza existente para manter vínculo usuário↔cliente (email é a chave de vínculo)
        upd = await db.fetchrow(
            """UPDATE clientes SET nome=$1, email=$2, telefone=$3, cpf=$4 WHERE id=$5 RETURNING id, nome, email, telefone, cpf""",
            cliente.nome, cliente.email, cliente.telefone, cliente.cpf, existentes['id']
        )
        return dict(upd)
    clientes = await db.fetchrow(
        """INSERT INTO clientes (nome, email, telefone, cpf) VALUES ($1,$2,$3,$4) RETURNING id, nome, email, telefone, cpf""",
        cliente.nome, cliente.email, cliente.telefone, cliente.cpf,
    )
    return dict(clientes) if clientes else {}


@router.get('/', response_model=ClientesList)
async def get_clientes(filtrar: Annotated[ClientesFilter, Depends()], db: dbConnection):
    query = 'SELECT id, nome, email, telefone, cpf FROM clientes WHERE 1=1'

    params = []
    params_index = 1

    if filtrar.nome:
        query += f' AND nome ILIKE ${params_index}'
        params.append(f'%{filtrar.nome}%')
        params_index += 1

    if filtrar.email:
        query += f' AND email ILIKE ${params_index}'
        params.append(f'{filtrar.email.strip()}')
        params_index += 1

    if filtrar.telefone:
        query += f' AND telefone = ${params_index}'
        params.append(filtrar.telefone)
        params_index += 1

    if filtrar.cpf:
        query += f' AND cpf = ${params_index}'
        params.append(filtrar.cpf)
        params_index += 1

    query += f' OFFSET ${params_index} LIMIT ${params_index + 1}'

    params.append(filtrar.offset)
    params.append(filtrar.limit)

    result = await db.fetch(query, *params)

    if not result:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail='Cliente não encontrado')

    clientes = [dict(row) for row in result]

    return {'clientes': clientes}


@router.patch('/{cliente_id}', response_model=ClientesResponse, status_code=HTTPStatus.OK)
async def update_cliente(db: dbConnection, cliente: ClientesUpdate, cliente_id: int):
    query = await db.fetchrow('SELECT id FROM clientes WHERE id = $1', cliente_id)

    if not query:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail='Cliente não encontrado')

    if cliente.nome is not None:
        query = 'SELECT id, nome FROM clientes WHERE nome = $1 AND id != $2'
        nome_existe = await db.fetch(query, cliente.nome, cliente_id)

        if nome_existe:
            raise HTTPException(status_code=HTTPStatus.CONFLICT, detail='Já existe um cliente cadastrado com este nome')

    if cliente.email:
        query = 'SELECT id, email FROM clientes WHERE email = $1 AND id != $2'
        email_existe = await db.fetch(query, cliente.email, cliente_id)

        if email_existe:
            raise HTTPException(status_code=HTTPStatus.CONFLICT, detail='Já existe um cliente cadastrado com este email')

    if cliente.telefone:
        query = 'SELECT id, telefone FROM clientes WHERE telefone = $1 AND id != $2'
        telefone_existe = await db.fetch(query, cliente.telefone, cliente_id)

        if telefone_existe:
            raise HTTPException(status_code=HTTPStatus.CONFLICT, detail='Já existe um cliente cadastrado com este telefone')

    if cliente.cpf:
        query = 'SELECT id, cpf FROM clientes WHERE cpf = $1 AND id != $2'
        cpf_existe = await db.fetch(query, cliente.cpf, cliente_id)

        if cpf_existe:
            raise HTTPException(status_code=HTTPStatus.CONFLICT, detail='Já existe um cliente cadastrado com este cpf')

    update_data = cliente.model_dump(exclude_unset=True)

    if not update_data:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail='Nenhum campo para atualizar')

    set_clauses = []
    params = []
    params_index = 1

    for field, values in update_data.items():
        set_clauses.append(f'{field} = ${params_index}')
        params.append(values)
        params_index += 1

    params.append(cliente_id)

    set_query = ', '.join(set_clauses)

    query = f"""
    UPDATE clientes
    SET {set_query}
    WHERE id = ${params_index}
    RETURNING id, nome, email, telefone, cpf
    """

    result = await db.fetchrow(query, *params)
    if not result:
        raise HTTPException(status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail='Erro ao atualizar')

    return dict(result)


@router.delete('/{cliente_id}', status_code=HTTPStatus.OK, response_model=Message)
async def delete_cliente(cliente_id: int, db: dbConnection):
    query = await db.execute('DELETE FROM clientes WHERE id = $1', cliente_id)

    if query == 'DELETE 0':
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail='Cliente não encontrado')

    return {'message': 'Cliente deletado da loja virtual'}
