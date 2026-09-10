import os
import uuid
from http import HTTPStatus
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from api.security import get_current_admin

router = APIRouter(prefix='/upload', tags=['upload'])

CurrentUser = Annotated[dict, Depends(get_current_admin)]

ALLOWED_TYPES = {
    'image/jpeg': '.jpg',
    'image/png': '.png',
    'image/webp': '.webp',
}

BLOB_API_URL = 'https://blob.vercel-storage.com'
MAX_SIZE = 5 * 1024 * 1024  # 5MB por arquivo
MAX_FILES = 8


def _blob_token() -> str:
    token = os.environ.get('BLOB_READ_WRITE_TOKEN', '')
    if not token:
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail='Upload indisponível: BLOB_READ_WRITE_TOKEN não configurado.',
        )
    return token


async def _put_blob(client: httpx.AsyncClient, token: str, filename: str, content: bytes, content_type: str) -> str:
    try:
        response = await client.put(
            f'{BLOB_API_URL}/{filename}',
            content=content,
            headers={
                'Authorization': f'Bearer {token}',
                'x-content-type': content_type,
                'x-api-version': '7',
            },
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as e:
        detalhe = ''
        try:
            detalhe = f": {e.response.text[:200]}"
        except Exception:
            pass
        raise HTTPException(
            status_code=HTTPStatus.BAD_GATEWAY,
            detail=f'Falha ao enviar para o Blob ({e.response.status_code}){detalhe}',
        ) from e
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=HTTPStatus.BAD_GATEWAY,
            detail=f'Falha de rede ao enviar para o Blob: {str(e)[:150]}',
        ) from e
    try:
        return response.json()['url']
    except Exception as e:
        raise HTTPException(
            status_code=HTTPStatus.BAD_GATEWAY,
            detail='Resposta inesperada do Blob.',
        ) from e


@router.post('/imagem', status_code=HTTPStatus.CREATED)
async def upload_imagem(
    files: list[UploadFile] = File(default=[]),
    file: UploadFile | None = File(default=None),
    current_user: CurrentUser = None,
):
    """Envia 1 ou várias imagens para o Vercel Blob.

    Aceita tanto `files` (novo, múltiplo) quanto `file` (legado, único).
    Retorna `urls` (lista) e, por compatibilidade, `url`/`filename` do primeiro.
    """
    token = _blob_token()

    todos = list(files or [])
    if file is not None:
        todos.append(file)
    files = todos

    if not files:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail='Nenhum arquivo enviado.')
    if len(files) > MAX_FILES:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=f'Máximo de {MAX_FILES} imagens por vez.',
        )

    conteudos: list[tuple[str, bytes, str]] = []
    for f in files:
        if f.content_type not in ALLOWED_TYPES:
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST,
                detail=f'Tipo não suportado ({f.filename or "arquivo"}). Aceitos: jpg, png, webp',
            )
        content = await f.read()
        if not content:
            raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail='Arquivo vazio.')
        if len(content) > MAX_SIZE:
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST,
                detail=f'Arquivo muito grande ({f.filename or "arquivo"}). Máximo: 5MB.',
            )
        conteudos.append((f.content_type, content, ALLOWED_TYPES[f.content_type]))

    urls: list[str] = []
    filenames: list[str] = []
    async with httpx.AsyncClient(timeout=30.0) as client:
        for content_type, content, ext in conteudos:
            filename = f'{uuid.uuid4().hex}{ext}'
            url = await _put_blob(client, token, filename, content, content_type)
            urls.append(url)
            filenames.append(filename)

    return {'urls': urls, 'url': urls[0], 'filenames': filenames, 'filename': filenames[0]}
