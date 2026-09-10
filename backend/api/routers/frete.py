from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import Annotated, Optional

import asyncpg

from api.database import get_db
from api.security import get_current_admin
from api.services.correios import calcular_frete, peso_taxavel, validar_dimensoes

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

def _extrair_valor_prazo(resposta: dict, co_produto: str, fallback_valor: float, fallback_prazo: int) -> tuple[float, int]:
    """Extrai valor e prazo da resposta heterogênea da API dos Correios.

    A API CWS pode devolver formatos diferentes conforme versão/ambiente
    (lista de itens, dict aninhado, strings com vírgula decimal). O parser é
    defensivo: tenta vários caminhos e cai no fallback calculado por peso.
    """
    valor, prazo = fallback_valor, fallback_prazo
    if not isinstance(resposta, dict):
        return valor, prazo
    candidatos = []
    for chave in ('preco', 'precos', 'dados', 'itens', 'result', 'resultado'):
        v = resposta.get(chave)
        if isinstance(v, list):
            candidatos.extend(v)
        elif isinstance(v, dict):
            candidatos.append(v)
    candidatos.append(resposta)
    for item in candidatos:
        if not isinstance(item, dict):
            continue
        for k in ('vlTotal', 'valor', 'preco', 'price', 'vl_preco'):
            raw = item.get(k)
            if raw is None:
                continue
            try:
                if isinstance(raw, str):
                    raw = raw.replace('R$', '').strip().replace('.', '').replace(',', '.') if ',' in raw else raw
                num = float(raw)
                if num > 0:
                    valor = round(num, 2)
                    break
            except (ValueError, TypeError):
                continue
        for k in ('prazoEntrega', 'prazo', 'dias', 'prazo_dias'):
            raw = item.get(k)
            if raw is None:
                continue
            try:
                num = int(str(raw).split()[0])
                if num > 0:
                    prazo = num
                    break
            except (ValueError, TypeError, IndexError):
                continue
    return valor, prazo


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

        # Se sem credenciais, retorna mock para teste
        from api.settings import settings
        # 1) Melhor Envio (produção, sem contrato próprio)
        if settings.MELHORENVIO_TOKEN:
            from api.services.melhorenvio import calcular as calcular_me
            try:
                opcoes = await calcular_me(
                    req.cepDestino, ps, comp, larg, alt,
                    valor_declarado=float(req.vlDeclarado or 0),
                    db=db,
                )
            except Exception as e:
                # Cai para o Correios/mock abaixo em vez de quebrar o checkout
                import logging as _lgme
                _lgme.getLogger('frete').warning('Melhor Envio falhou, tentando Correios: %s', str(e)[:200])
            else:
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
        if not settings.CORREIOS_USER:
            # mock: R$ 18 + 0.02 por grama taxavel + prazo 5 dias
            mock_valor = round(18 + (taxavel/1000)*4,2)
            return {
                "cepDestino": req.cepDestino,
                "pesoReal": ps,
                "pesoCubadoKg": round((comp*larg*alt)/6000,2),
                "pesoTaxavel": taxavel,
                "dimensoes": {"comp":comp,"larg":larg,"alt":alt},
                "mock": True,
                "opcoes": [
                    {"servico":"PAC","coProduto":"04510","valor":mock_valor,"prazo":5},
                    {"servico":"SEDEX","coProduto":"04014","valor":round(mock_valor*1.6,2),"prazo":2},
                ]
            }

        res = await calcular_frete(req.cepDestino, ps, comp, larg, alt, req.tpObjeto or 2, req.vlDeclarado, req.coProduto)
        # Normaliza a resposta real dos Correios para o mesmo formato do mock
        # (o frontend sempre espera `opcoes`). Nunca retorna prazo/preco crus.
        from api.settings import settings as _s
        base_mock = round(18 + (taxavel / 1000) * 4, 2)
        try:
            prazo_raw, preco_raw = res.get('prazo', {}), res.get('preco', {})
            v_pac, p_pac = _extrair_valor_prazo(preco_raw if isinstance(preco_raw, dict) else {}, _s.CORREIOS_CO_PRODUTO_PAC, base_mock, 5)
            # tenta extrair prazo do payload de prazo separadamente
            _, p_pac2 = _extrair_valor_prazo(prazo_raw if isinstance(prazo_raw, dict) else {}, _s.CORREIOS_CO_PRODUTO_PAC, v_pac, p_pac)
            v_sedex, p_sedex = _extrair_valor_prazo(preco_raw if isinstance(preco_raw, dict) else {}, _s.CORREIOS_CO_PRODUTO_SEDEX, round(base_mock * 1.6, 2), 2)
            _, p_sedex2 = _extrair_valor_prazo(prazo_raw if isinstance(prazo_raw, dict) else {}, _s.CORREIOS_CO_PRODUTO_SEDEX, v_sedex, p_sedex)
            opcoes = [
                {'servico': 'PAC', 'coProduto': _s.CORREIOS_CO_PRODUTO_PAC, 'valor': v_pac, 'prazo': p_pac2},
                {'servico': 'SEDEX', 'coProduto': _s.CORREIOS_CO_PRODUTO_SEDEX, 'valor': v_sedex, 'prazo': p_sedex2},
            ]
        except Exception:
            opcoes = [
                {'servico': 'PAC', 'coProduto': _s.CORREIOS_CO_PRODUTO_PAC, 'valor': base_mock, 'prazo': 5},
                {'servico': 'SEDEX', 'coProduto': _s.CORREIOS_CO_PRODUTO_SEDEX, 'valor': round(base_mock * 1.6, 2), 'prazo': 2},
            ]
        return {
            'cepDestino': req.cepDestino,
            'pesoReal': ps,
            'pesoCubadoKg': round((comp * larg * alt) / 6000, 2),
            'pesoTaxavel': taxavel,
            'dimensoes': {'comp': comp, 'larg': larg, 'alt': alt},
            'opcoes': opcoes,
            'mock': False,
            'raw': {'prazo': res.get('prazo'), 'preco': res.get('preco')},
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
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
