import os
import uuid
import httpx
from http import HTTPStatus
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from typing import Annotated

from api.security import get_current_admin

router = APIRouter(prefix='/upload', tags=['upload'])

CurrentUser = Annotated[dict, Depends(get_current_admin)]

ALLOWED_TYPES = {
    'image/jpeg': '.jpg',
    'image/png': '.png',
    'image/webp': '.webp',
}

BLOB_READ_WRITE_TOKEN = os.environ['BLOB_READ_WRITE_TOKEN']
BLOB_API_URL = 'https://blob.vercel-storage.com'


@router.post('/imagem', status_code=HTTPStatus.CREATED)
async def upload_imagem(file: UploadFile = File(...), current_user: CurrentUser = None):
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail='Tipo de arquivo nao suportado. Aceitos: jpg, png, webp',
        )

    ext = ALLOWED_TYPES[file.content_type]
    filename = f'{uuid.uuid4().hex}{ext}'

    content = await file.read()

    max_size = 5 * 1024 * 1024  # 5MB
    if len(content) > max_size:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail='Arquivo muito grande. Tamanho maximo: 5MB',
        )

    async with httpx.AsyncClient() as client:
        response = await client.put(
            f'{BLOB_API_URL}/{filename}',
            content=content,
            headers={
                'Authorization': f'Bearer {BLOB_READ_WRITE_TOKEN}',
                'x-content-type': file.content_type,
                'x-api-version': '7',
            },
        )
        response.raise_for_status()
        blob_data = response.json()

    return {'url': blob_data['url'], 'filename': filename}
