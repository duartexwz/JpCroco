from http import HTTPStatus
from typing import Annotated

import asyncpg
from fastapi import APIRouter, Depends, HTTPException

from api.database import get_db
from api.schemas.pedidos_schemas import Message
from api.schemas.usuarios_schemas import FilterUsuario, UsuarioList, UsuarioResponse, UsuarioSchema, UsuarioUpdate
from api.security import get_current_admin, get_current_user, get_password_hash

router = APIRouter(prefix='/usuarios', tags=['usuarios'])


database_loja = Annotated[asyncpg.Connection, Depends(get_db)]
CurrentUser = Annotated[dict, Depends(get_current_user)]
CurrentAdmin = Annotated[dict, Depends(get_current_admin)]


@router.post('/', status_code=HTTPStatus.CREATED, response_model=UsuarioResponse)
async def create_usuario( db: database_loja, usuario: UsuarioSchema):
    query = 'SELECT id FROM usuarios WHERE username = $1'

    usuario_existe = await db.fetchrow(query, usuario.username)

    if usuario_existe:
        raise HTTPException(status_code=HTTPStatus.CONFLICT, detail='O usuário já possui um cadastro, tente realizar o login.')

    insert_query = """
    INSERT INTO usuarios (username, password, acesso, nome_completo)
    VALUES ($1, $2, $3, $4)
    RETURNING id, username, acesso, nome_completo
    """

    hashed_password = get_password_hash(usuario.password)
    result = await db.fetchrow(insert_query, usuario.username, hashed_password, usuario.acesso, usuario.nome_completo)

    return dict(result) if result else {}


@router.get('/', response_model=UsuarioList, status_code=HTTPStatus.OK)
async def get_usuarios(filtrar: Annotated[FilterUsuario, Depends()], db: database_loja, usuario_id: int | None = None):
    query = 'SELECT id, username, acesso, nome_completo FROM usuarios WHERE 1=1'
    params = []
    param_index = 1

    target_usuario_id = usuario_id or getattr(filtrar, 'id', None)

    if filtrar.username:
        query += f' AND username ILIKE ${param_index}'
        params.append(f'%{filtrar.username}%')
        param_index += 1

    if target_usuario_id:
        query += f' AND id = ${param_index}'
        params.append(target_usuario_id)
        param_index += 1

    query += f' OFFSET ${param_index} LIMIT ${param_index + 1}'

    params.append(filtrar.offset)
    params.append(filtrar.limit)

    result = await db.fetch(query, *params)

    usuarios = [dict(row) for row in result]

    return {'usuarios': usuarios}


@router.patch('/{usuario_id}', response_model=UsuarioResponse, status_code=HTTPStatus.OK)
async def update_usuario(usuario: UsuarioUpdate, db: database_loja, current_user: CurrentUser, usuario_id: int):

    query = await db.fetchrow('SELECT id FROM usuarios WHERE id = $1', usuario_id)

    if not query:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail='Usuário não encontrado.')

    if usuario.username is not None:
        query_usuario = 'SELECT id FROM usuarios WHERE username = $1 AND id != $2'
        usuario_existente = await db.fetchrow(query_usuario, usuario.username, usuario_id)

        if usuario_existente:
            raise HTTPException(status_code=HTTPStatus.CONFLICT, detail='Já existe um usuário cadastrado com este username.')

    update_data = usuario.model_dump(exclude_unset=True)

    if not update_data:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail='Nenhum campo inserido na atualização.')

    set_clauses = []
    params = []
    param_index = 1

    for field, value in update_data.items():
        set_clauses.append(f'{field} = ${param_index}')
        params.append(value)
        param_index += 1

    params.append(usuario_id)

    set_query = ','.join(set_clauses)

    inset_query = f"""
    UPDATE usuarios
    SET {set_query}
    WHERE id = ${param_index}
    RETURNING id, username, acesso, nome_completo
    """

    result = await db.fetchrow(inset_query, *params)

    if result is None:
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail='Ocorreu um erro ao atualizar o usuário, tente novamente mais tarde.'
        )

    return dict(result)


@router.delete('/{usuario_id}', response_model=Message, status_code=HTTPStatus.OK)
async def deletar_usuario(usuario_id: int, current_user: CurrentAdmin, db: database_loja):
    query = await db.fetchrow('DELETE FROM usuarios WHERE id = $1 RETURNING id', usuario_id)

    if not query:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail='Usuário não encontrado.')

    return {'message': 'Usuário deletado da loja virtual.'}
