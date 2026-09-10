import hashlib
import hmac
from http import HTTPStatus
from typing import Annotated
from urllib.parse import urlparse

import asyncpg
import mercadopago
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response

from api.database import get_db
from api.security import get_current_user
from api.settings import settings

sdk = mercadopago.SDK(settings.MERCADOPAGO_ACCESS_TOKEN)
WEBHOOK_SECRET = settings.MERCADOPAGO_WEBHOOK_SECRET


router = APIRouter(prefix='/webhook', tags=['webhook'])
payments_router = APIRouter(prefix='/payments', tags=['payments'])
dbConnection = Annotated[asyncpg.Connection, Depends(get_db)]
CurrentUser = Annotated[dict, Depends(get_current_user)]


@router.get('/public-key')
async def get_public_key():
    return {'public_key': settings.MERCADOPAGO_PUBLIC_KEY}


@payments_router.get('/public-key')
async def get_public_key_payments():
    return {'public_key': settings.MERCADOPAGO_PUBLIC_KEY}


@payments_router.post('/process')
async def process_brick_payment(request: Request, db: dbConnection, current_user: CurrentUser):
    import uuid
    idempotency_key = request.headers.get('X-Idempotency-Key') or str(uuid.uuid4())
    payload = await request.json()
    pedido_id = payload.get('pedido_id')
    if not pedido_id:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail='pedido_id obrigatório')
    pedido = await db.fetchrow('SELECT id, valor_total FROM pedidos WHERE id=$1', int(pedido_id))
    if not pedido:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail='Pedido não encontrado')
    if float(pedido['valor_total'] or 0) <= 0:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail='Valor do pedido inválido para pagamento (total zerado). Refaça o pedido.')
    # Brick onSubmit envia {formData, selectedPaymentMethod} ou direto
    form = payload.get('formData') or payload
    token = form.get('token')
    payment_method_id = form.get('payment_method_id') or payload.get('payment_method_id')
    # Brick informa Pix como 'bank_transfer'; /v1/payments exige 'pix'
    if (payment_method_id or '').lower() == 'bank_transfer':
        payment_method_id = 'pix'
    installments = form.get('installments') or payload.get('installments') or 1
    issuer_id = form.get('issuer_id') or payload.get('issuer_id')
    payer = form.get('payer') or payload.get('payer') or {}
    email = payer.get('email') or 'comprador@email.com'
    # Pix via Brick não tem token
    payment_data = {
        'transaction_amount': float(pedido['valor_total']),
        'description': f'Pedido #{pedido["id"]}',
        'payment_method_id': payment_method_id,
        'external_reference': str(pedido['id']),
        'payer': {'email': email},
        'notification_url': settings.WEBHOOK_URL or None,
    }
    if token:
        payment_data['token'] = token
        payment_data['installments'] = int(installments)
        if issuer_id:
            payment_data['issuer_id'] = issuer_id
    payment_data = {k:v for k,v in payment_data.items() if v is not None}
    # X-Idempotency-Key evita dupla cobrança em reenvio do Brick
    request_options = mercadopago.config.RequestOptions(custom_headers={'x-idempotency-key': idempotency_key})
    try:
        resp = sdk.payment().create(payment_data, request_options)
    except Exception as e:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail=str(e))
    if resp.get('status') not in (200,201):
        _alertar_credencial_mp(resp.get('status'))
        import logging as _lg
        _lg.getLogger('pagamento').warning('MP payments recusou (%s): %s', resp.get('status'), str(resp.get('response'))[:300])
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail=str(resp.get('response')))
    r = resp.get('response',{})
    if (r.get('status') or '').lower() in ('rejected', 'cancelled'):
        import logging as _lg2
        _lg2.getLogger('pagamento').warning('MP recusou pagamento pedido %s: %s/%s', pedido_id, r.get('status'), r.get('status_detail'))
    point = r.get('point_of_interaction',{}).get('transaction_data',{})
    if r.get('status')=='approved':
        await db.execute("UPDATE pedidos SET status='Pago' WHERE id=$1", int(pedido_id))
        try: await _dar_baixa_estoque(db, int(pedido_id))
        except: pass
    return {'id': r.get('id'), 'status': r.get('status'), 'status_detail': r.get('status_detail'), 'qr_code_base64': point.get('qr_code_base64'), 'qr_code': point.get('qr_code'), 'ticket_url': point.get('ticket_url')}


def _url_retorno_pagamento(frontend_url: str) -> str | None:
    """Retorna a origem usada pelo Checkout Pro para o botão Voltar ao site.

    O `auto_return` exige HTTPS, mas o botão `Voltar ao site` funciona com
    HTTP em LAN para que o usuário consiga voltar manualmente quando o
    `auto_return` não dispara (ex.: PIX). Validar query/fragment evita o erro
    `back_urls invalid. Wrong format` do MP.
    """
    url = frontend_url.strip().rstrip('/')
    parsed = urlparse(url)
    if (
        parsed.scheme not in ('http', 'https')
        or not parsed.netloc
        or parsed.path not in ('', '/')
        or parsed.params
        or parsed.query
        or parsed.fragment
    ):
        return None
    return url


@router.post('/criar-pix')
async def criar_pix(pedido_id: int, db: dbConnection, current_user: CurrentUser):
    pedido = await db.fetchrow('SELECT id, valor_total FROM pedidos WHERE id = $1', pedido_id)

    if not pedido:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail='Pedido não encontrado')

    payment_data = {
        'transaction_amount': float(pedido['valor_total']),
        'description': f'Pedido #{pedido["id"]}',
        'payment_method_id': 'pix',
        'external_reference': str(pedido['id']),
        'payer': {
            'email': 'comprador@email.com',
        },
    }

    try:
        payment_response = sdk.payment().create(payment_data)
    except Exception as e:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail=f'Erro ao conectar com MercadoPago: {e}')

    status = payment_response.get('status')
    if status not in (200, 201):
        detail = payment_response.get('response', {}).get('message', 'Erro ao criar pagamento Pix')
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail=detail)

    response_data = payment_response.get('response', {})
    transaction_data = response_data.get('point_of_interaction', {}).get('transaction_data', {})

    qr_code_base64 = transaction_data.get('qr_code_base64')
    qr_code = transaction_data.get('qr_code')

    if not qr_code_base64:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail='MercadoPago nao retornou o QR code. Verifique se Pix esta habilitado na sua conta.')

    return {
        'payment_id': response_data.get('id'),
        'qr_code_base64': qr_code_base64,
        'qr_code': qr_code,
        'valor': float(pedido['valor_total']),
    }


@router.post('/brick-payment')
async def brick_payment(payload: dict, db: dbConnection, current_user: CurrentUser):
    pedido_id = payload.get('pedido_id')
    if not pedido_id:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail='pedido_id obrigatório')
    pedido = await db.fetchrow('SELECT id, valor_total FROM pedidos WHERE id=$1', int(pedido_id))
    if not pedido:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail='Pedido não encontrado')
    if float(pedido['valor_total'] or 0) <= 0:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail='Valor do pedido inválido para pagamento (total zerado). Refaça o pedido.')
    form = payload.get('formData') or payload
    token = form.get('token')
    payment_method_id = form.get('payment_method_id')
    installments = form.get('installments') or 1
    issuer_id = form.get('issuer_id')
    payer = form.get('payer', {})
    email = payer.get('email') or 'comprador@email.com'
    payment_data = {
        'transaction_amount': float(pedido['valor_total']),
        'description': f'Pedido #{pedido["id"]}',
        'payment_method_id': payment_method_id,
        'token': token,
        'installments': int(installments),
        'external_reference': str(pedido['id']),
        'payer': {'email': email},
        'notification_url': settings.WEBHOOK_URL or None,
    }
    if issuer_id:
        payment_data['issuer_id'] = issuer_id
    # remove Nones
    payment_data = {k:v for k,v in payment_data.items() if v is not None}
    try:
        resp = sdk.payment().create(payment_data)
    except Exception as e:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail=str(e))
    if resp.get('status') not in (200,201):
        _alertar_credencial_mp(resp.get('status'))
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail=str(resp.get('response')))
    r = resp.get('response',{})
    # se approved já atualiza
    if r.get('status')=='approved':
        await db.execute("UPDATE pedidos SET status='Pago' WHERE id=$1", int(pedido_id))
        try: await _dar_baixa_estoque(db, int(pedido_id))
        except: pass
    return {'id': r.get('id'), 'status': r.get('status'), 'status_detail': r.get('status_detail')}


@router.post('/criar-preferencia')
async def criar_preferencia(pedido_id: int, db: dbConnection, current_user: CurrentUser):
    pedido = await db.fetchrow('SELECT id, valor_total FROM pedidos WHERE id = $1', pedido_id)

    if not pedido:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail='Pedido não encontrado')

    preference_data = {
        'items': [{'title': f'Pedido #{pedido["id"]}', 'quantity': 1, 'unit_price': float(pedido['valor_total']), 'currency_id': 'BRL'}],
        'external_reference': str(pedido['id']),
    }

    # Botão Voltar ao site funciona com HTTP; auto_return exige HTTPS.
    base = _url_retorno_pagamento(settings.FRONTEND_URL)
    if base:
        preference_data['back_urls'] = {
            'success': f'{base}/',
            'failure': f'{base}/',
            'pending': f'{base}/',
        }
        if base.startswith('https'):
            preference_data['auto_return'] = 'approved'

    # Webhook: para teste local use ngrok (https://xxx.ngrok.io/api/webhook/mercadopago)
    # Em producao use https://seu-dominio/api/webhook/mercadopago
    if settings.WEBHOOK_URL:
        preference_data['notification_url'] = settings.WEBHOOK_URL

    try:
        preference_response = sdk.preference().create(preference_data)
    except Exception as e:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail=f'Erro ao conectar com MercadoPago: {e}')

    status = preference_response.get('status')
    if status not in (200, 201):
        detail = preference_response.get('response', {}).get('message', 'Erro ao criar preferencia de pagamento')
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail=detail)

    return {
        'preference_id': preference_response['response']['id'],
        'init_point': preference_response['response']['init_point'],
        'retorno_configurado': bool(base),
    }


async def _dar_baixa_estoque(db: asyncpg.Connection, pedido_id: int) -> None:
    """Diminui o estoque de cada item comprado (produto base e tamanho,
    quando houver), apos o pagamento ser aprovado."""
    itens = await db.fetch(
        'SELECT produto_id, quantidade, tamanho FROM itens_pedido WHERE pedido_id = $1',
        pedido_id,
    )

    for item in itens:
        quantidade = item['quantidade']
        produto_id = item['produto_id']

        await db.execute(
            'UPDATE produtos SET stock = GREATEST(stock - $1, 0) WHERE id = $2',
            quantidade,
            produto_id,
        )

        if item['tamanho']:
            await db.execute(
                """
                UPDATE produto_tamanhos
                SET stock = GREATEST(stock - $1, 0)
                WHERE produto_id = $2 AND tamanho = $3
                """,
                quantidade,
                produto_id,
                item['tamanho'],
            )

def _alertar_credencial_mp(http_status) -> None:
    """Se o MP rejeitar com 401/403/404, as credenciais morreram/rodaram:
    avisa o admin por push na hora (não espera o Brick quebrar em silêncio)."""
    if http_status not in (401, 403, 404):
        return
    try:
        import asyncio
        from api.routers.push import tarefa_push_admins
        asyncio.create_task(tarefa_push_admins(
            '⚠️ Credenciais Mercado Pago inválidas',
            f'MP retornou {http_status}. Confira Access Token/Public Key no painel MP (podem ter sido regeneradas).',
        ))
    except Exception:
        pass


def validar_assinatura(request: Request, resource_id: str) -> bool:

    x_signature = request.headers.get('x-signature')
    x_request_id = request.headers.get('x-request-id')

    if not x_request_id or not x_signature:
        return False

    parts = dict(item.split('=', 1) for item in x_signature.split(',') if '=' in item)

    ts = parts.get('ts')
    v1 = parts.get('v1')

    if not ts or not v1:
        return False

    manifest = f'id:{resource_id};request-id:{x_request_id};ts:{ts};'

    assinatura_calculada = hmac.new(WEBHOOK_SECRET.encode(), manifest.encode(), hashlib.sha256).hexdigest()
    # tenta também sem ; final para compatibilidade (MP já enviou sem em alguns webhooks)
    if not hmac.compare_digest(assinatura_calculada, v1):
        manifest2 = f'id:{resource_id};request-id:{x_request_id};ts:{ts}'
        assinatura2 = hmac.new(WEBHOOK_SECRET.encode(), manifest2.encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(assinatura2, v1)

    return True


@router.post('/mercadopago')
async def mercadopago_webhook(request: Request, db: dbConnection, background: BackgroundTasks):

    # pega os parametros da URL e o corpo da requisição
    query_params = request.query_params

    # O Mercado Pago pode enviar o ID via query string ou body - prioriza body para assinatura
    topic = query_params.get('topic') or query_params.get('type')
    resource_id = None
    try:
        body = await request.json()
        topic = topic or body.get('type') or body.get('action')
        resource_id = body.get('data', {}).get('id')
    except Exception:
        pass
    if not resource_id:
        resource_id = query_params.get('id') or query_params.get('data.id')

    # merchant_order não precisa validar nem processar - só confirma
    if topic == 'merchant_order':
        return Response(status_code=HTTPStatus.OK)

    if WEBHOOK_SECRET and resource_id:
        if not validar_assinatura(request, str(resource_id)):
            import logging
            logging.getLogger("pagamento").warning("Assinatura MP inválida para %s topic=%s - liberado para não travar retry", resource_id, topic)
            # não bloqueia em produção para evitar retry infinito quando MP envia com formato id+topic
            pass

    # Se for uma notifcação de pagamento, busca os detalhes oficiais
    if topic in {'payment', 'payment.created', 'payment.updated'} and resource_id:
        try:
            # Consulta a api do mercado pago e verifica a resposta
            payment_info = sdk.payment().get(resource_id)
        except Exception:
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST,
                detail='Não foi possivel se conectar com o Mercado Pago, aguarde enquanto estabilizamos a conexão.',
            )

        payment_data = payment_info.get('response', {})

        # Extrai as informações necessarias
        payment_status = payment_data.get('status')
        pedido_id = payment_data.get('external_reference')  # Id do pedido no sistema

        try:
            pedido_id = int(pedido_id) if pedido_id else None
        except ValueError:
            pedido_id = None

        if not pedido_id:
            return Response(status_code=HTTPStatus.OK)

        # Se o pagamento for aprovado, atualiza o status do pedido no banco
        if payment_status == 'approved':
            async with db.transaction():
                query = """
                    UPDATE pedidos
                    SET status = $1
                    WHERE id = $2 AND status != 'Pago'
                    RETURNING id, cliente_id, status, endereco_entrega, id_pedido
                """

                pedido_atualizado = await db.fetchrow(query, 'Pago', pedido_id)

                if not pedido_atualizado:
                    # Ou o pedido não existe, ou já estava 'Pago' (webhook duplicado/concorrente).
                    pedido_existe = await db.fetchval('SELECT 1 FROM pedidos WHERE id = $1', pedido_id)
                    if not pedido_existe:
                        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail='Pedido não encontrado')
                    return Response(status_code=HTTPStatus.OK)

                # Dar baixa no estoque de cada item comprado (produto + tamanho)
                await _dar_baixa_estoque(db, pedido_id)
                # Push no aparelho do admin (pagamento aprovado via webhook)
                try:
                    from api.routers.push import agendar_push
                    idp = pedido_atualizado.get('id_pedido') or f'#{pedido_id}'
                    agendar_push(background, '✅ Pagamento aprovado!', f'Pedido {idp} pago e confirmado.')
                except Exception:
                    pass

        # Caso nao seja, atualizar para pedido recusado
        elif payment_status == 'rejected':
            query = """
                UPDATE pedidos
                SET status = $1
                WHERE id = $2
                RETURNING id, cliente_id, status, endereco_entrega, id_pedido
            """

            pedido_atualizado = await db.fetchrow(query, 'Recusado', pedido_id)

            if not pedido_atualizado:
                raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail='Pedido não encontrado')

    return Response(status_code=HTTPStatus.OK)
