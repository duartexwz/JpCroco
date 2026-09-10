import re

import httpx
from fastapi import APIRouter, HTTPException


router = APIRouter(prefix='/endereco', tags=['endereco'])


@router.get('/cep/{cep}')
async def consultar_cep(cep: str):
    """Consulta um CEP no ViaCEP e devolve apenas os campos usados no checkout."""
    cep_numerico = re.sub(r'\D', '', cep)
    if len(cep_numerico) != 8:
        raise HTTPException(status_code=400, detail='CEP deve ter 8 dígitos')

    try:
        async with httpx.AsyncClient(timeout=6.0) as client:
            resposta = await client.get(f'https://viacep.com.br/ws/{cep_numerico}/json/')
            resposta.raise_for_status()
            dados = resposta.json()
    except httpx.HTTPError:
        raise HTTPException(status_code=503, detail='Não foi possível consultar o CEP. Tente novamente.')

    if dados.get('erro'):
        raise HTTPException(status_code=404, detail='CEP não encontrado')

    return {
        'cep': dados.get('cep', ''),
        'rua': dados.get('logradouro', ''),
        'bairro': dados.get('bairro', ''),
        'cidade': dados.get('localidade', ''),
        'estado': dados.get('uf', ''),
    }
