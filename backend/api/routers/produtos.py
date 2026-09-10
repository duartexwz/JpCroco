from http import HTTPStatus
from typing import Annotated

import asyncpg
from fastapi import APIRouter, Depends, HTTPException

from api.database import get_db
from api.schemas.pedidos_schemas import Message
from api.schemas.produtos_schemas import FilterProdutos, ProdutosList, ProdutosResponse, ProdutosSchema, ProdutosUpdate
from api.security import get_current_admin, get_current_user

router = APIRouter(
    prefix='/produtos',
    tags=['produtos'],
)

database_loja = Annotated[asyncpg.Connection, Depends(get_db)]
CurrentUser = Annotated[dict, Depends(get_current_user)]
CurrentAdmin = Annotated[dict, Depends(get_current_admin)]


async def _get_tamanhos(db: asyncpg.Connection, produto_id: int) -> list[dict]:
    rows = await db.fetch(
        'SELECT tamanho, stock, preco FROM produto_tamanhos WHERE produto_id = $1 ORDER BY id',
        produto_id,
    )
    return [dict(r) for r in rows]


async def _get_imagens(db: asyncpg.Connection, produto_id: int) -> list[str]:
    rows = await db.fetch(
        'SELECT url FROM produto_imagens WHERE produto_id = $1 ORDER BY ordem, id',
        produto_id,
    )
    urls = [r['url'] for r in rows]
    if not urls and produto_id:
        cover = await db.fetchval('SELECT imagem FROM produtos WHERE id = $1', produto_id)
        if cover:
            urls = [cover]
    return urls


async def _save_imagens(db: asyncpg.Connection, produto_id: int, imagens: list[str]) -> None:
    """Substitui as imagens de um produto na tabela produto_imagens."""
    await db.execute('DELETE FROM produto_imagens WHERE produto_id = $1', produto_id)
    for i, url in enumerate(imagens):
        if not url:
            continue
        await db.execute(
            'INSERT INTO produto_imagens (produto_id, url, ordem) VALUES ($1, $2, $3)',
            produto_id, url, i,
        )


async def _serialize(db: asyncpg.Connection, produto: dict) -> dict:
    dados = dict(produto)
    dados['tamanhos'] = await _get_tamanhos(db, produto['id'])
    dados['imagens'] = await _get_imagens(db, produto['id'])
    return dados


@router.post('/', response_model=ProdutosResponse, status_code=HTTPStatus.CREATED)
async def create_produto(produto: ProdutosSchema, db: database_loja, current_user: CurrentAdmin):
    check_query = 'SELECT id FROM produtos WHERE nome = $1'
    produto_existente = await db.fetchrow(check_query, produto.nome)

    if produto_existente:
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT,
            detail='Já existe outro produto com esse nome.',
        )

    tamanhos = produto.tamanhos or []
    tamanho_base = tamanhos[0].tamanho if tamanhos else None
    stock_base = sum(t.stock for t in tamanhos) if tamanhos else 0

    imagens = produto.imagens or ([produto.imagem] if produto.imagem else [])
    imagem_cover = imagens[0] if imagens else None

    insert_query = """
    INSERT INTO produtos (nome, preco, tamanho, stock, imagem, preco_promocional)
    VALUES ($1, $2, $3, $4, $5, $6)
    RETURNING id, nome, preco, tamanho, stock, imagem, preco_promocional
    """
    result = await db.fetchrow(
        insert_query,
        produto.nome,
        produto.preco,
        tamanho_base,
        stock_base,
        imagem_cover,
        produto.preco_promocional,
    )

    if not result:
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail='Falha ao criar o produto.',
        )

    produto_id = result['id']
    for t in tamanhos:
        preco_var = t.preco if t.preco is not None else produto.preco
        await db.execute(
            'INSERT INTO produto_tamanhos (produto_id, tamanho, stock, preco) VALUES ($1, $2, $3, $4)',
            produto_id, t.tamanho, t.stock, preco_var,
        )

    if imagens:
        await _save_imagens(db, produto_id, imagens)

    return await _serialize(db, result)


@router.get('/', response_model=ProdutosList, status_code=HTTPStatus.OK)
async def listar_produtos(filtrar: Annotated[FilterProdutos, Depends()], db: database_loja):
    query = 'SELECT id, nome, preco, tamanho, stock, imagem, preco_promocional FROM produtos WHERE 1=1'
    params = []
    param_index = 1

    if filtrar.nome:
        query += f' AND nome ILIKE ${param_index}'
        params.append(f'%{filtrar.nome}%')
        param_index += 1

    if filtrar.preco_min is not None:
        query += f' AND preco >= ${param_index}'
        params.append(filtrar.preco_min)
        param_index += 1

    if filtrar.preco_max is not None:
        query += f' AND preco <= ${param_index}'
        params.append(filtrar.preco_max)
        param_index += 1

    if filtrar.tamanho:
        query = query + f'\nAND id IN (SELECT produto_id FROM produto_tamanhos WHERE tamanho = ${param_index})'
        params.append(filtrar.tamanho)
        param_index += 1

    if filtrar.stock_min is not None:
        query += f' AND stock >= ${param_index}'
        params.append(filtrar.stock_min)
        param_index += 1

    if filtrar.stock_max is not None:
        query += f' AND stock <= ${param_index}'
        params.append(filtrar.stock_max)
        param_index += 1

    query += f' OFFSET ${param_index} LIMIT ${param_index + 1}'
    params.append(filtrar.offset)
    params.append(filtrar.limit)

    result = await db.fetch(query, *params)

    produtos = []
    for row in result:
        dados = dict(row)
        dados['tamanhos'] = await _get_tamanhos(db, row['id'])
        dados['imagens'] = await _get_imagens(db, row['id'])
        produtos.append(dados)

    return {'produtos': produtos}


@router.patch('/{produto_id}', response_model=ProdutosResponse, status_code=HTTPStatus.OK)
async def atualizar_produto(produto_id: int, produto: ProdutosUpdate, db: database_loja, current_user: CurrentAdmin):
    produto_db = await db.fetchrow('SELECT id, preco FROM produtos WHERE id = $1', produto_id)
    if not produto_db:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail='Produto não encontrado')

    if produto.nome is not None:
        check_query = 'SELECT id FROM produtos WHERE nome = $1 AND id != $2'
        produto_existente = await db.fetchrow(check_query, produto.nome, produto_id)

        if produto_existente:
            raise HTTPException(
                status_code=HTTPStatus.CONFLICT,
                detail='Já existe um produto com esse nome.',
            )

    update_data = produto.model_dump(exclude_unset=True)
    update_veio = bool(update_data)
    tem_tamanhos = 'tamanhos' in update_data and update_data['tamanhos'] is not None
    tem_imagens = 'imagens' in update_data and update_data['imagens'] is not None
    update_data.pop('tamanhos', None)
    update_data.pop('imagens', None)

    if not update_data and not tem_tamanhos and not tem_imagens:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail='Nenhum campo inserido na atualização.',
        )

    if update_data:
        set_clauses = []
        params = []
        param_index = 1

        for field, value in update_data.items():
            set_clauses.append(f'{field} = ${param_index}')
            params.append(value)
            param_index += 1

        params.append(produto_id)

        set_query = ' ,'.join(set_clauses)
        query = f"""
            UPDATE produtos
            SET {set_query}
            WHERE id = ${param_index}
            RETURNING id, nome, preco, tamanho, stock, imagem, preco_promocional
        """

        result = await db.fetchrow(query, *params)

        if result is None:
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                detail='Falha ao atualizar o produto.',
            )
    else:
        result = await db.fetchrow(
            'SELECT id, nome, preco, tamanho, stock, imagem, preco_promocional FROM produtos WHERE id = $1',
            produto_id,
        )

    if produto.tamanhos is not None:
        await db.execute('DELETE FROM produto_tamanhos WHERE produto_id = $1', produto_id)
        preco_base = produto_db['preco']
        for t in produto.tamanhos:
            preco_var = t.preco if t.preco is not None else preco_base
            await db.execute(
                'INSERT INTO produto_tamanhos (produto_id, tamanho, stock, preco) VALUES ($1, $2, $3, $4)',
                produto_id, t.tamanho, t.stock, preco_var,
            )
        stock_total = sum(t.stock for t in produto.tamanhos)
        tam_base = produto.tamanhos[0].tamanho if produto.tamanhos else None
        await db.execute(
            'UPDATE produtos SET stock = $1, tamanho = $2 WHERE id = $3',
            stock_total, tam_base, produto_id,
        )
        result = await db.fetchrow(
            'SELECT id, nome, preco, tamanho, stock, imagem, preco_promocional FROM produtos WHERE id = $1',
            produto_id,
        )

    if tem_imagens:
        await _save_imagens(db, produto_id, produto.imagens)
        nova_cover = produto.imagens[0] if produto.imagens else None
        await db.execute(
            'UPDATE produtos SET imagem = $1 WHERE id = $2',
            nova_cover, produto_id,
        )
        result = await db.fetchrow(
            'SELECT id, nome, preco, tamanho, stock, imagem, preco_promocional FROM produtos WHERE id = $1',
            produto_id,
        )

    return await _serialize(db, result)


@router.delete('/{produto_id}', status_code=HTTPStatus.OK, response_model=Message)
async def deletar_produto(produto_id: int, db: database_loja, current_user: CurrentAdmin):
    exists = await db.fetchval('SELECT id FROM produtos WHERE id = $1', produto_id)
    if exists is None:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Produto não encontrado.',
        )

    referenced = await db.fetchval(
        'SELECT 1 FROM itens_pedido WHERE produto_id = $1 LIMIT 1', produto_id
    )
    if referenced is not None:
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT,
            detail='Não é possível excluir este produto pois ele está associado a um ou mais pedidos.',
        )

    await db.execute('DELETE FROM produtos WHERE id = $1', produto_id)

    return {'message': 'Produto deletado do estoque virtual'}
