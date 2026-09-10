"""Integração SuperFrete (produção) — cálculo de frete.

Docs: https://superfrete.readme.io — base prod https://api.superfrete.com
(sandbox: https://sandbox.superfrete.com). Token por ambiente, gerado em
#/integrations. Auth: Bearer + User-Agent obrigatório com e-mail.
"""
import httpx

from api.settings import settings


CEP_LEN = 8


def _headers(token: str) -> dict:
    return {
        'Authorization': f'Bearer {token}',
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'User-Agent': f"JP Croco 1.0 ({settings.SUPERFRETE_EMAIL or settings.MELHORENVIO_EMAIL or 'contato@jpcroco.com.br'})",
    }


def _servicos_permitidos() -> set[str] | None:
    raw = (settings.SUPERFRETE_SERVICES or '').strip()
    if not raw:
        return None
    return {s.strip() for s in raw.split(',') if s.strip()}


async def calcular(
    cep_destino: str,
    peso_gramas: int,
    comp: int,
    larg: int,
    alt: int,
    valor_declarado: float = 0,
) -> list[dict]:
    """Cota e devolve opções no formato do frontend: servico/valor/prazo.

    `coProduto` carrega 'SF:<service_id>' para a futura compra da etiqueta.
    """
    cep_dest = ''.join(c for c in cep_destino if c.isdigit())
    cep_orig = ''.join(c for c in settings.CEP_ORIGEM if c.isdigit())
    if len(cep_dest) != CEP_LEN or len(cep_orig) != CEP_LEN:
        raise ValueError('CEP origem/destino deve ter 8 dígitos')
    token = (settings.SUPERFRETE_TOKEN or '').strip()
    if not token:
        raise ValueError('Token SuperFrete não configurado (SUPERFRETE_TOKEN).')

    peso_kg = max(round(peso_gramas / 1000, 2), 0.01)
    payload = {
        'from': {'postal_code': cep_orig},
        'to': {'postal_code': cep_dest},
        'services': '1,2,17',
        'options': {
            'own_hand': False,
            'receipt': False,
            'insurance_value': round(float(valor_declarado or 0), 2),
            'use_insurance_value': bool(valor_declarado),
        },
        'products': [{
            'quantity': 1,
            'height': alt,
            'length': comp,
            'width': larg,
            'weight': peso_kg,
        }],
    }
    base = settings.SUPERFRETE_API_URL.rstrip('/')
    permitidos = _servicos_permitidos()
    async with httpx.AsyncClient(timeout=20) as client:
        try:
            r = await client.post(f'{base}/api/v0/calculator', json=payload, headers=_headers(token))
        except httpx.HTTPError as e:
            raise RuntimeError(f'Falha de rede na SuperFrete: {str(e)[:150]}')
    if r.status_code not in {200, 201}:
        raise RuntimeError(f'SuperFrete recusou ({r.status_code}): {(r.text or "")[:300]}')
    try:
        dados = r.json()
    except Exception:
        raise RuntimeError('Resposta inválida da SuperFrete (não-JSON).')
    servicos = dados if isinstance(dados, list) else dados.get('data', [])

    opcoes = []
    for s in servicos if isinstance(servicos, list) else []:
        if not isinstance(s, dict) or s.get('has_error'):
            continue
        sid = str(s.get('id', ''))
        if permitidos and sid not in permitidos:
            continue
        try:
            valor = float(s.get('price', 0))
        except (ValueError, TypeError):
            continue
        if valor <= 0:
            continue
        try:
            prazo = int(str(s.get('delivery_time', 0)).split()[0])
        except (ValueError, TypeError, IndexError):
            prazo = 0
        company = s.get('company') or {}
        nome = f"{company.get('name', '')} {s.get('name', '')}".strip() or f'Serviço {sid}'
        opcoes.append({
            'servico': nome,
            'coProduto': f'SF:{sid}',
            'valor': round(valor, 2),
            'prazo': prazo,
        })
    opcoes.sort(key=lambda o: o['valor'])
    if not opcoes:
        raise RuntimeError('SuperFrete não retornou opções para este CEP.')
    return opcoes
