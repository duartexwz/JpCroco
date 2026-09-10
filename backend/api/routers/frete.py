from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import Annotated, Optional

import asyncpg

from api.database import get_db
from api.security import get_current_admin
from api.services.melhorenvio import calcular as calcular_me

router = APIRouter(prefix='/frete', tags=['frete'])

dbConnection = Annotated[asyncpg.Connection, Depends(get_db)]
AdminUser = Annotated[dict, Depends(get_current_admin)]

# DF (70/71 e parte de 73) e cidades do Entorno atendidas localmente (72/73).
# Para esses CEPs a loja não deve consultar nem expor dados dos Correios.
CEP_DF_ENTORNO_PREFIXOS = ('70', '71', '72', '73')


class CalcularFreteRequest(BaseModel):
    cepDestino: str
    psObjeto: Optional[int] = None  # se não enviar, soma dos produtos
    comprimento: Optional[int] = 20
    largura: Optional[int] = 15
    altura: Optional[int] = 10
    tpObjeto: Optional[int] = 2
    vlDeclarado: Optional[float] = None
    coProduto: Optional[str] = None
    # para cálculo por carrinho: lista de produto_ids + qtd
    itens: Optional[list[dict]] = None


def peso_taxavel(psObjeto_g: int, comp: int, larg: int, alt: int) -> int:
    cubado_kg = (comp * larg * alt) / 6000
    if cubado_kg <= 5:
        return psObjeto_g
    cubado_g = int(cubado_kg * 1000)
    return max(psObjeto_g, cubado_g)


def validar_dimensoes(comp: int, larg: int, alt: int):
    soma = comp + larg + alt
    if not (15 <= comp <= 100):
        raise ValueError('Comprimento deve ser 15-100cm')
    if not (10 <= larg <= 100):
        raise ValueError('Largura deve ser 10-100cm')
    if not (1 <= alt <= 100):
        raise ValueError('Altura deve ser 1-100cm')
    if not (29 <= soma <= 200):
        raise ValueError('Soma C+L+A deve ser 29-200cm')


@router.post('/calcular')
async def calcular(req: CalcularFreteRequest, db: dbConnection):
    try:
        cep_num = "".join(c for c in req.cepDestino if c.isdigit())
        if len(cep_num) != 8:
            raise ValueError("CEP destino deve ter 8 dígitos")

        # Entrega local não depende de peso, cubagem ou consulta aos Correios.
        if cep_num.startswith(CEP_DF_ENTORNO_PREFIXOS):
            return {
                "cepDestino": req.cepDestino,
                "entregaLocal": True,
                "brasilia": True,
                "opcoes": [
                    {"servico": "Retirada no local", "coProduto": "RETIRADA", "valor": 0, "prazo": 0, "obs": "Grátis"},
                    {"servico": "Uber Delivery", "coProduto": "UBER", "valor": 0, "prazo": 0, "obs": "Valor combinado após a compra"},
                ],
                "aviso": "Para DF e Entorno, escolha retirada no local ou Uber Delivery.",
            }

        # Se itens enviados, calcula peso/dimensões agregados (simplificado: maior caixa + soma pesos)
        if req.itens:
            # itens: [{peso_gramas, comprimento, largura, altura, quantidade}]
            total_peso = 0
            max_c = req.comprimento or 20
            max_l = req.largura or 15
            max_a = 0
            for it in req.itens:
                qtd = it.get('quantidade',1)
                total_peso += (it.get('peso_gramas',500) * qtd)
                max_a += (it.get('altura',10) * qtd)  # empilha altura
                max_c = max(max_c, it.get('comprimento',20))
                max_l = max(max_l, it.get('largura',15))
            ps = total_peso
            comp, larg, alt = max_c, max_l, min(max_a,100)
        else:
            ps = req.psObjeto or 1000
            comp, larg, alt = req.comprimento, req.largura, req.altura

        validar_dimensoes(comp,larg,alt)
        taxavel = peso_taxavel(ps, comp,larg,alt)

        # Melhor Envio é o único provedor (sem mock: preço chutado cobraria frete errado).
        from api.settings import settings
        if not settings.MELHORENVIO_TOKEN:
            raise HTTPException(
                status_code=502,
                detail='Frete indisponível: token do Melhor Envio não configurado.',
            )
        try:
            opcoes = await calcular_me(
                req.cepDestino, ps, comp, larg, alt,
                valor_declarado=float(req.vlDeclarado or 0),
                db=db,
            )
        except (ValueError, RuntimeError) as e:
            raise HTTPException(status_code=502, detail=str(e))
        return {
            'cepDestino': req.cepDestino,
            'pesoReal': ps,
            'pesoCubadoKg': round((comp * larg * alt) / 6000, 2),
            'pesoTaxavel': taxavel,
            'dimensoes': {'comp': comp, 'larg': larg, 'alt': alt},
            'opcoes': opcoes,
            'mock': False,
            'provedor': 'melhorenvio',
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


class EtiquetaRequest(BaseModel):
    service_id: int  # ex: 1 PAC, 2 SEDEX, 3 Jadlog Package, 4 Jadlog Com


@router.post('/etiqueta/{pedido_id}')
async def gerar_etiqueta(pedido_id: int, body: EtiquetaRequest, db: dbConnection, admin: AdminUser, background: BackgroundTasks):
    """Compra a etiqueta no Melhor Envio (cobra a carteira!), salva o
    rastreio e marca Enviado — cliente é notificado sozinho."""
    from api.services import melhorenvio as me
    from api.services.notificacao import notificar_rastreio

    pedido = await db.fetchrow('SELECT * FROM pedidos WHERE id = $1', pedido_id)
    if not pedido:
        raise HTTPException(status_code=404, detail='Pedido não encontrado')
    pedido = dict(pedido)
    if (pedido.get('status') or '').lower() not in ('pago', 'aprovado', 'approved'):
        raise HTTPException(status_code=400, detail='Etiqueta só após o pagamento (pedido precisa estar Pago).')
    if pedido.get('codigo_rastreio'):
        raise HTTPException(status_code=400, detail='Pedido já tem rastreio.')

    cliente = await db.fetchrow('SELECT nome, email, telefone, cpf FROM clientes WHERE id = $1', pedido.get('cliente_id'))
    if not cliente:
        raise HTTPException(status_code=400, detail='Cliente do pedido não encontrado.')
    cliente = dict(cliente)
    try:
        destino = me.parse_endereco(pedido.get('endereco_entrega') or '')
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    doc_cli = ''.join(c for c in (cliente.get('cpf') or '') if c.isdigit())
    para = {
        'name': (cliente.get('nome') or 'Cliente')[:60],
        'phone': ''.join(c for c in (cliente.get('telefone') or '') if c.isdigit()),
        'email': cliente.get('email') or '',
        'document': doc_cli,
        **destino,
    }

    itens = await db.fetch(
        '''SELECT i.quantidade, i.preco_unitario, p.nome, p.peso_gramas,
                  p.comprimento, p.largura, p.altura
           FROM itens_pedido i JOIN produtos p ON p.id = i.produto_id
           WHERE i.pedido_id = $1''',
        pedido_id,
    )
    if not itens:
        raise HTTPException(status_code=400, detail='Pedido sem itens.')
    produtos, peso_total, max_c, max_l, soma_a = [], 0, 20, 15, 0
    for it in itens:
        qtd = it['quantidade'] or 1
        produtos.append({'name': (it['nome'] or 'Produto')[:60], 'quantity': qtd, 'unitary_value': float(it['preco_unitario'] or 0)})
        peso_total += (it['peso_gramas'] or 500) * qtd
        max_c = max(max_c, it['comprimento'] or 20)
        max_l = max(max_l, it['largura'] or 15)
        soma_a += (it['altura'] or 10) * qtd
    volume = {'height': min(soma_a, 100), 'width': max_l, 'length': max_c, 'weight': max(round(peso_total / 1000, 2), 0.01)}

    try:
        etq = await me.comprar_etiqueta(
            body.service_id, para, produtos, volume,
            seguro=float(pedido.get('valor_total') or 0),
            pedido_ref=pedido.get('id_pedido') or f'#{pedido_id}',
            db=db,
        )
    except (ValueError, RuntimeError) as e:
        raise HTTPException(status_code=502, detail=str(e))

    atualizado = await db.fetchrow(
        """UPDATE pedidos SET codigo_rastreio = $1, status = 'Enviado', data_envio = NOW()
           WHERE id = $2 RETURNING id, id_pedido, status, codigo_rastreio, transportadora, cliente_id""",
        etq['tracking'], pedido_id,
    )
    try:
        background.add_task(notificar_rastreio, cliente, dict(atualizado))
    except Exception:
        pass
    return {'tracking': etq['tracking'], 'label_url': etq['label_url'], 'order_id': etq['order_id']}


@router.get('/oauth/url')
async def oauth_url(db: dbConnection, admin: AdminUser):
    """Devolve a URL de autorização OAuth (admin clica, autoriza no ME)."""
    from api.services import melhorenvio as me
    return {'authorize_url': me.authorize_url()}


@router.get('/oauth/callback')
async def oauth_callback(code: str | None = None, db: dbConnection = None):
    """Retorno OAuth do Melhor Envio: troca o code pelos tokens e salva."""
    from api.services import melhorenvio as me
    if not code:
        raise HTTPException(status_code=400, detail='Parâmetro code ausente.')
    try:
        dados = await me.trocar_code(code, db)
    except (ValueError, RuntimeError) as e:
        raise HTTPException(status_code=502, detail=str(e))
    return {'ok': True, 'expira_em': dados.get('expira_em')}


@router.get('/melhorenvio-webhook')
async def melhorenvio_webhook_check():
    """Responde à verificação de cadastro do painel ME (teste via GET)."""
    return {'ok': True}


@router.post('/melhorenvio-webhook')
async def melhorenvio_webhook(request: Request):
    """Recebe eventos do Melhor Envio (tracking da etiqueta etc.).

    URL pública p/ cadastrar no painel ME:
    https://jpcroco.vercel.app/api/frete/melhorenvio-webhook
    Por enquanto registra o evento; o vínculo com o pedido entra na
    fase 2 (compra de etiqueta).
    """
    import logging
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    logging.getLogger('frete').info('Webhook ME: %s', str(payload)[:500])
    return {'ok': True}
