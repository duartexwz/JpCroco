"""Integração Melhor Envio (produção) — cálculo de frete sem contrato próprio.

Docs: https://docs.melhorenvio.com.br — base prod
https://www.melhorenvio.com.br/api/v2 (sandbox: ...sandbox.melhorenvio...).
Autenticação: Bearer <token> + header User-Agent com e-mail (exigido pelo ME).
"""
import re
import time
from datetime import datetime, timezone
from urllib.parse import urlencode

import httpx

from api.settings import settings

CEP_LEN = 8
# Margem para renovar o token OAuth antes de vencer
REFRESH_MARGIN = 120

OAUTH_SCOPES = (
    'cart-read cart-write shipping-calculate shipping-checkout '
    'shipping-companies shipping-generate shipping-preview shipping-print '
    'shipping-share shipping-tracking'
)


def _api_base() -> str:
    return settings.MELHORENVIO_API_URL.rstrip('/')


def _oauth_base() -> str:
    base = _api_base()
    return base[:-len('/api/v2')] if base.endswith('/api/v2') else base


def authorize_url() -> str:
    if not settings.MELHORENVIO_CLIENT_ID:
        raise ValueError('MELHORENVIO_CLIENT_ID não configurado.')
    qs = urlencode({
        'client_id': settings.MELHORENVIO_CLIENT_ID,
        'redirect_uri': settings.MELHORENVIO_REDIRECT_URI,
        'response_type': 'code',
        'scope': OAUTH_SCOPES,
    })
    return f'{_oauth_base()}/oauth/authorize?{qs}'


async def trocar_code(code: str, db) -> dict:
    """Troca o code do callback pelos tokens e salva (upsert linha única)."""
    if not settings.MELHORENVIO_CLIENT_ID or not settings.MELHORENVIO_CLIENT_SECRET:
        raise ValueError('Credenciais OAuth do Melhor Envio incompletas.')
    async with httpx.AsyncClient(timeout=20) as client:
        try:
            r = await client.post(f'{_oauth_base()}/oauth/token', data={
                'grant_type': 'authorization_code',
                'client_id': settings.MELHORENVIO_CLIENT_ID,
                'client_secret': settings.MELHORENVIO_CLIENT_SECRET,
                'redirect_uri': settings.MELHORENVIO_REDIRECT_URI,
                'code': code,
            }, headers={'Accept': 'application/json'})
        except httpx.HTTPError as e:
            raise RuntimeError(f'ME oauth: falha de rede: {str(e)[:150]}')
    if r.status_code not in {200, 201}:
        raise RuntimeError(f'ME oauth recusou ({r.status_code}): {(r.text or "")[:200]}')
    try:
        data = r.json()
    except Exception:
        raise RuntimeError('ME oauth: resposta não-JSON.')
    access, refresh = data.get('access_token'), data.get('refresh_token', '')
    if not access:
        raise RuntimeError(f'ME oauth sem access_token: {str(data)[:200]}')
    expira_em = time.time() + int(data.get('expires_in', 2592000))
    await db.execute(
        """INSERT INTO melhorenvio_tokens (id, access_token, refresh_token, expires_at, updated_at)
           VALUES (1, $1, $2, $3, CURRENT_TIMESTAMP)
           ON CONFLICT (id) DO UPDATE SET access_token = EXCLUDED.access_token,
             refresh_token = EXCLUDED.refresh_token, expires_at = EXCLUDED.expires_at,
             updated_at = CURRENT_TIMESTAMP""",
        access, refresh,
        datetime.fromtimestamp(expira_em, tz=timezone.utc).replace(tzinfo=None),
    )
    return {'ok': True, 'expira_em': int(expira_em)}


async def token_resolvido(db=None) -> str:
    """Token OAuth do banco (renova sozinho) ou o fixo do .env."""
    if db is not None:
        try:
            row = await db.fetchrow('SELECT access_token, refresh_token, expires_at FROM melhorenvio_tokens WHERE id = 1')
        except Exception:
            row = None
        if row and row['access_token']:
            exp = row['expires_at'].timestamp() if row['expires_at'] else 0
            if exp - time.time() > REFRESH_MARGIN:
                return row['access_token']
            if row['refresh_token']:
                try:
                    async with httpx.AsyncClient(timeout=20) as client:
                        r = await client.post(f'{_oauth_base()}/oauth/token', data={
                            'grant_type': 'refresh_token',
                            'client_id': settings.MELHORENVIO_CLIENT_ID,
                            'client_secret': settings.MELHORENVIO_CLIENT_SECRET,
                            'refresh_token': row['refresh_token'],
                        }, headers={'Accept': 'application/json'})
                    data = r.json()
                    if data.get('access_token'):
                        exp2 = time.time() + int(data.get('expires_in', 2592000))
                        await db.execute(
                            'UPDATE melhorenvio_tokens SET access_token = $1, expires_at = $2, updated_at = CURRENT_TIMESTAMP WHERE id = 1',
                            data['access_token'],
                            datetime.fromtimestamp(exp2, tz=timezone.utc).replace(tzinfo=None),
                        )
                        return data['access_token']
                except Exception:
                    pass
                return row['access_token']
    token = (settings.MELHORENVIO_TOKEN or '').strip()
    if not token:
        raise ValueError('Token Melhor Envio não configurado (nem OAuth nem MELHORENVIO_TOKEN).')
    return token


# "Rua X, 123 - compl, Bairro, Cidade - UF, CEP: 12345-678" (v2, com bairro)
# "Rua X, 123 - compl, Cidade - UF, CEP: 12345-678" (v1, sem bairro)
_RE_V2 = re.compile(
    r'^(?P<rua>.+?),\s*(?P<numero>\S+?)(?:\s*-\s*(?P<compl>.+?))?,\s*(?P<bairro>.+?),\s*'
    r'(?P<cidade>.+?)\s*-\s*(?P<uf>[A-Za-z]{2})\s*,\s*CEP:\s*(?P<cep>[\d-]+)\s*$'
)
_RE_V1 = re.compile(
    r'^(?P<rua>.+?),\s*(?P<numero>\S+?)(?:\s*-\s*(?P<compl>.+?))?,\s*'
    r'(?P<cidade>.+?)\s*-\s*(?P<uf>[A-Za-z]{2})\s*,\s*CEP:\s*(?P<cep>[\d-]+)\s*$'
)


def parse_endereco(texto: str) -> dict:
    """Quebra o endereco gravado no pedido nos campos da etiqueta."""
    t = (texto or '').strip()
    m = _RE_V2.match(t) or _RE_V1.match(t)
    if not m:
        raise ValueError('Endereço do pedido fora do padrão; edite o pedido antes de gerar a etiqueta.')
    d = m.groupdict()
    cep = ''.join(c for c in (d.get('cep') or '') if c.isdigit())
    if len(cep) != CEP_LEN:
        raise ValueError('CEP do pedido inválido.')
    return {
        'address': (d.get('rua') or '').strip(),
        'number': (d.get('numero') or '').strip(),
        'complement': (d.get('compl') or '').strip(),
        'district': (d.get('bairro') or '').strip(),
        'city': (d.get('cidade') or '').strip(),
        'state_abbr': (d.get('uf') or '').strip().upper(),
        'postal_code': cep,
        'country_id': 'BR',
    }


def _headers(token: str) -> dict:
    return {
        'Authorization': f'Bearer {token}',
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'User-Agent': settings.MELHORENVIO_EMAIL or 'contato@jpcroco.com.br',
    }


def _servicos_permitidos() -> set[str] | None:
    raw = (settings.MELHORENVIO_SERVICES or '').strip()
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
    quantidade: int = 1,
    db=None,
) -> list[dict]:
    """Cota e devolve opções no formato do frontend: servico/valor/prazo.

    `coProduto` carrega 'ME:<service_id>' para a futura compra da etiqueta.
    """
    cep_dest = ''.join(c for c in cep_destino if c.isdigit())
    cep_orig = ''.join(c for c in settings.CEP_ORIGEM if c.isdigit())
    if len(cep_dest) != CEP_LEN or len(cep_orig) != CEP_LEN:
        raise ValueError('CEP origem/destino deve ter 8 dígitos')
    token = await token_resolvido(db)

    peso_kg = max(round(peso_gramas / 1000, 2), 0.01)
    payload = {
        'from': {'postal_code': cep_orig},
        'to': {'postal_code': cep_dest},
        'products': [{
            'id': 'caixa',
            'width': larg,
            'height': alt,
            'length': comp,
            'weight': peso_kg,
            'insurance_value': round(float(valor_declarado or 0), 2),
            'quantity': max(int(quantidade or 1), 1),
        }],
    }
    base = settings.MELHORENVIO_API_URL.rstrip('/')
    permitidos = _servicos_permitidos()
    async with httpx.AsyncClient(timeout=20) as client:
        try:
            r = await client.post(f'{base}/me/shipment/calculate', json=payload, headers=_headers(token))
        except httpx.HTTPError as e:
            raise RuntimeError(f'Falha de rede no Melhor Envio: {str(e)[:150]}')
    if r.status_code not in {200, 201}:
        raise RuntimeError(f'Melhor Envio recusou ({r.status_code}): {(r.text or "")[:300]}')
    try:
        dados = r.json()
    except Exception:
        raise RuntimeError('Resposta inválida do Melhor Envio (não-JSON).')
    servicos = dados if isinstance(dados, list) else dados.get('data', dados)

    opcoes = []
    for s in servicos if isinstance(servicos, list) else []:
        if not isinstance(s, dict) or s.get('error'):
            continue
        sid = str(s.get('id', ''))
        if permitidos and sid not in permitidos:
            continue
        try:
            valor = float(str(s.get('price', s.get('discounted_price', 0))).replace(',', '.'))
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
            'coProduto': f'ME:{sid}',
            'valor': round(valor, 2),
            'prazo': prazo,
        })
    opcoes.sort(key=lambda o: o['valor'])
    if not opcoes:
        raise RuntimeError('Melhor Envio não retornou opções para este CEP.')
    return opcoes


def _sender() -> dict:
    s = settings
    faltando = [k for k in ('MELHORENVIO_FROM_NOME', 'MELHORENVIO_FROM_DOCUMENTO', 'MELHORENVIO_FROM_ENDERECO',
                            'MELHORENVIO_FROM_NUMERO', 'MELHORENVIO_FROM_BAIRRO', 'MELHORENVIO_FROM_CIDADE',
                            'MELHORENVIO_FROM_UF', 'MELHORENVIO_FROM_CEP', 'MELHORENVIO_FROM_TELEFONE',
                            'MELHORENVIO_FROM_EMAIL') if not (getattr(s, k, '') or '').strip()]
    if faltando:
        raise ValueError('Remetente incompleto no .env (MELHORENVIO_FROM_*).')
    doc = ''.join(c for c in s.MELHORENVIO_FROM_DOCUMENTO if c.isdigit())
    cep = ''.join(c for c in s.MELHORENVIO_FROM_CEP if c.isdigit())
    return {
        'name': s.MELHORENVIO_FROM_NOME.strip(),
        'phone': ''.join(c for c in s.MELHORENVIO_FROM_TELEFONE if c.isdigit()),
        'email': s.MELHORENVIO_FROM_EMAIL.strip(),
        'document': doc,
        'address': s.MELHORENVIO_FROM_ENDERECO.strip(),
        'complement': (s.MELHORENVIO_FROM_COMPLEMENTO or '').strip(),
        'number': s.MELHORENVIO_FROM_NUMERO.strip(),
        'district': s.MELHORENVIO_FROM_BAIRRO.strip(),
        'city': s.MELHORENVIO_FROM_CIDADE.strip(),
        'state_abbr': s.MELHORENVIO_FROM_UF.strip().upper(),
        'country_id': 'BR',
        'postal_code': cep,
    }


async def _me_post(client: httpx.AsyncClient, caminho: str, payload: dict, etapa: str, token: str) -> dict:
    base = settings.MELHORENVIO_API_URL.rstrip('/')
    try:
        r = await client.post(f'{base}{caminho}', json=payload, headers=_headers(token))
    except httpx.HTTPError as e:
        raise RuntimeError(f'ME {etapa}: falha de rede: {str(e)[:150]}')
    if r.status_code not in {200, 201}:
        raise RuntimeError(f'ME {etapa} recusou ({r.status_code}): {(r.text or "")[:300]}')
    try:
        data = r.json()
    except Exception:
        raise RuntimeError(f'ME {etapa}: resposta não-JSON.')
    return data if isinstance(data, dict) else {'data': data}


async def comprar_etiqueta(
    service_id: int,
    para: dict,
    produtos: list[dict],
    volume: dict,
    seguro: float,
    pedido_ref: str,
    db=None,
) -> dict:
    """Fluxo completo: carrinho → checkout (cobra carteira!) → etiqueta.

    Retorna {tracking, label_url, order_id, protocol}.
    """
    de = _sender()
    token = await token_resolvido(db)
    async with httpx.AsyncClient(timeout=30) as client:
        cart = await _me_post(client, '/me/cart', {
            'service': int(service_id),
            'from': de,
            'to': para,
            'products': produtos,
            'volumes': [volume],
            'options': {
                'insurance_value': round(float(seguro or 0), 2),
                'receipt': False,
                'own_hand': False,
                'reverse': False,
                'non_commercial': False,
                'platform': 'JP Croco',
                'reminder': f'Pedido {pedido_ref}',
            },
        }, 'carrinho', token)
        cart_id = cart.get('id')
        if not cart_id:
            raise RuntimeError(f'ME carrinho sem id: {str(cart)[:200]}')
        await _me_post(client, '/me/shipment/checkout', {'orders': [cart_id]}, 'checkout', token)
        gen = await _me_post(client, '/me/shipment/generate', {'orders': [cart_id]}, 'etiqueta', token)
        tracking = gen.get('tracking') or gen.get('melhorenvio_tracking') or ''
        label_url = gen.get('url') or gen.get('label_url') or gen.get('print_url') or ''
        if not tracking:
            raise RuntimeError(f'ME gerou sem rastreio: {str(gen)[:300]}')
        return {'tracking': tracking, 'label_url': label_url, 'order_id': cart_id, 'protocol': gen.get('protocol', '')}
