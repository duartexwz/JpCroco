from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException

import asyncpg
from api.database import get_db

router = APIRouter(prefix='/rastreio', tags=['rastreio'])

# Mapeamento SRO CWS -> STEP (backend traduz para UI)
# STEP 1: Objeto Postado (PO, PE) | STEP 2: Em Trânsito (RO, DO, PAR, FC) | STEP 3: Saiu para Entrega (OEC) | STEP 4: Entregue (BDE/BDI)
STEP_DEFS = [
    {"id": 1, "label": "Objeto Postado", "label_en": "Order Placed"},
    {"id": 2, "label": "Em Trânsito", "label_en": "In Transit"},
    {"id": 3, "label": "Saiu para Entrega", "label_en": "Out For Delivery"},
    {"id": 4, "label": "Entregue", "label_en": "Delivered"},
]

def _step_por_evento(ev: dict) -> int:
    codigo = (ev.get("codigo") or ev.get("codEvento") or ev.get("tipo") or "").upper()
    desc = (ev.get("descricao") or ev.get("evento") or ev.get("status") or ev.get("detalhe") or "").lower()
    # código direto
    if codigo in ("PO", "PE", "PM"): return 1
    if codigo in ("RO", "DO", "CO", "PAR", "FC", "LDI"): return 2
    if codigo in ("OEC", "SCE"): return 3
    if codigo in ("BDE", "BDI", "BDE01", "ENT"): return 4
    if "postado" in desc: return 1
    if "saiu para entrega" in desc or "saiu para a entrega" in desc: return 3
    if "entregue" in desc: return 4
    if "trânsito" in desc or "transito" in desc or "encaminhado" in desc or "em trânsito" in desc: return 2
    return 0

def _normalizar_eventos(data) -> list[dict]:
    if isinstance(data, dict):
        # LinkCorreios: {"objetos":[{"eventos":[...]}]} ou {"eventos":[...]}
        if "objetos" in data and isinstance(data["objetos"], list) and data["objetos"]:
            return data["objetos"][0].get("eventos", [])
        if "eventos" in data: return data["eventos"]
        if "events" in data: return data["events"]
        # proxyapp: já é lista
        if isinstance(data, dict) and not data.get("codigo"):
            # tenta extrair valores
            for v in data.values():
                if isinstance(v, list): return v
        return [data]
    if isinstance(data, list): return data
    return []

dbConnection = Annotated[asyncpg.Connection, Depends(get_db)]

@router.get('/{codigo}')
async def rastrear(codigo: str, db: dbConnection):
    codigo = codigo.strip().upper()
    if len(codigo) < 8:
        raise HTTPException(status_code=400, detail='Código de rastreio inválido')
    urls = [
        f'https://api.linkcorreios.com.br/{codigo}',
        f'https://proxyapp.correios.com.br/v1/sro-rastro/{codigo}',
    ]
    last_error = None
    eventos_raw = None
    async with httpx.AsyncClient(timeout=10) as client:
        for url in urls:
            try:
                r = await client.get(url, headers={'Accept': 'application/json'})
                if r.status_code == 200:
                    eventos_raw = r.json()
                    break
                last_error = f'{url} -> {r.status_code}'
            except Exception as e:
                last_error = str(e)
                continue
    if eventos_raw is None:
        # Fallback: código de teste ou ainda não postado — usa status do pedido local
        try:
            pedido = await db.fetchrow("SELECT status, data_envio FROM pedidos WHERE codigo_rastreio = $1", codigo)
        except Exception:
            pedido = None
        if pedido:
            status = (pedido["status"] or "").lower()
            if status == "entregue": step_atual = 4
            elif status == "enviado": step_atual = 1
            elif status == "pago": step_atual = 1
            else: step_atual = 0
            steps = []
            for d in STEP_DEFS:
                ativo = d["id"] <= step_atual
                data_step = pedido["data_envio"].isoformat() if d["id"] == step_atual and pedido["data_envio"] else None
                steps.append({**d, "ativo": ativo, "data": data_step})
            return {
                "codigo": codigo,
                "step_atual": step_atual,
                "steps": steps,
                "eventos": [{"descricao": f"Pedido {status} - código {codigo} aguardando atualização nos Correios", "dtHrCriado": pedido["data_envio"].isoformat() if pedido["data_envio"] else None}],
                "aviso": "Código ainda não disponível nos Correios, exibindo status local",
            }
        # Sem pedido local, retorna 200 com aviso em vez de 502
        return {
            "codigo": codigo,
            "step_atual": 0,
            "steps": [{**d, "ativo": False, "data": None} for d in STEP_DEFS],
            "eventos": [],
            "aviso": f"Código não encontrado nos Correios: {last_error}. Verifique o código ou tente em https://www2.correios.com.br/sistemas/rastreamento/",
        }

    eventos = _normalizar_eventos(eventos_raw)
    # calcula step atual = maior step encontrado
    step_atual = 0
    for ev in eventos:
        s = _step_por_evento(ev)
        if s > step_atual: step_atual = s
    if not eventos: step_atual = 0

    steps = []
    for d in STEP_DEFS:
        ativo = d["id"] <= step_atual
        # pega data do primeiro evento que corresponde ao step
        data_step = None
        for ev in eventos:
            if _step_por_evento(ev) == d["id"]:
                data_step = ev.get("dtHrCriado") or ev.get("data") or ev.get("criado_em") or ev.get("dataHora")
                break
        steps.append({**d, "ativo": ativo, "data": data_step})

    return {
        "codigo": codigo,
        "step_atual": step_atual,
        "steps": steps,
        "eventos": eventos,
        "total_eventos": len(eventos),
    }
