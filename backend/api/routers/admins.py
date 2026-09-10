from http import HTTPStatus
from typing import Annotated

import asyncpg
from fastapi import APIRouter, Depends, HTTPException

from api.database import get_db
from api.schemas.admins_schemas import AdminList, AdminResponse, AdminSchema, AdminUpdate, FilterAdmin
from api.schemas.pedidos_schemas import Message
from api.security import get_current_admin, get_password_hash

router = APIRouter(prefix='/admins', tags=['admins'])

database_loja = Annotated[asyncpg.Connection, Depends(get_db)]
CurrentAdmin = Annotated[dict, Depends(get_current_admin)]


@router.post('/', status_code=HTTPStatus.CREATED, response_model=AdminResponse)
async def create_admin(db: database_loja, admin: AdminSchema, current_user: CurrentAdmin):
    query = 'SELECT id FROM admins WHERE username = $1'
    admin_existe = await db.fetchrow(query, admin.username)

    if admin_existe:
        raise HTTPException(status_code=HTTPStatus.CONFLICT, detail='Ja existe um admin com esse username.')

    insert_query = """
    INSERT INTO admins (username, password, acesso, nome_completo)
    VALUES ($1, $2, 'admin', $3)
    RETURNING id, username, nome_completo
    """

    hashed_password = get_password_hash(admin.password)
    result = await db.fetchrow(insert_query, admin.username, hashed_password, admin.nome_completo)

    return dict(result) if result else {}


@router.get('/', response_model=AdminList, status_code=HTTPStatus.OK)
async def get_admins(filtrar: Annotated[FilterAdmin, Depends()], db: database_loja):
    query = 'SELECT id, username, nome_completo FROM admins WHERE 1=1'
    params = []
    param_index = 1

    if filtrar.username:
        query += f' AND username ILIKE ${param_index}'
        params.append(f'%{filtrar.username}%')
        param_index += 1

    if filtrar.id:
        query += f' AND id = ${param_index}'
        params.append(filtrar.id)
        param_index += 1

    query += f' OFFSET ${param_index} LIMIT ${param_index + 1}'
    params.append(filtrar.offset)
    params.append(filtrar.limit)

    result = await db.fetch(query, *params)

    admins = [dict(row) for row in result]

    return {'admins': admins}


@router.patch('/{admin_id}', response_model=AdminResponse, status_code=HTTPStatus.OK)
async def update_admin(admin_id: int, admin: AdminUpdate, db: database_loja, current_user: CurrentAdmin):
    query = await db.fetchrow('SELECT id FROM admins WHERE id = $1', admin_id)

    if not query:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail='Admin nao encontrado.')

    if admin.username is not None:
        query_admin = 'SELECT id FROM admins WHERE username = $1 AND id != $2'
        admin_existente = await db.fetchrow(query_admin, admin.username, admin_id)

        if admin_existente:
            raise HTTPException(status_code=HTTPStatus.CONFLICT, detail='Ja existe um admin com esse username.')

    update_data = admin.model_dump(exclude_unset=True)

    if not update_data:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail='Nenhum campo inserido na atualizacao.')

    if 'password' in update_data:
        update_data['password'] = get_password_hash(update_data['password'])

    set_clauses = []
    params = []
    param_index = 1

    for field, value in update_data.items():
        set_clauses.append(f'{field} = ${param_index}')
        params.append(value)
        param_index += 1

    params.append(admin_id)

    set_query = ','.join(set_clauses)
    result_query = f"""
    UPDATE admins
    SET {set_query}
    WHERE id = ${param_index}
    RETURNING id, username, nome_completo
    """

    result = await db.fetchrow(result_query, *params)

    if result is None:
        raise HTTPException(status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail='Ocorreu um erro ao atualizar o admin.')

    return dict(result)


@router.delete('/{admin_id}', response_model=Message, status_code=HTTPStatus.OK)
async def deletar_admin(admin_id: int, current_user: CurrentAdmin, db: database_loja):
    query = await db.fetchrow('DELETE FROM admins WHERE id = $1 RETURNING id', admin_id)

    if not query:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail='Admin nao encontrado.')

    return {'message': 'Admin deletado com sucesso.'}
