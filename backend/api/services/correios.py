import base64
import time
from typing import Optional

import httpx

from api.settings import settings

_token_cache = {"token": None, "exp": 0}

async def _get_token() -> str:
    if not settings.CORREIOS_USER or not settings.CORREIOS_SENHA:
        raise ValueError("Credenciais Correios não configuradas (CORREIOS_USER/SENHA)")
    if _token_cache["token"] and time.time() < _token_cache["exp"] - 60:
        return _token_cache["token"]
    creds = f"{settings.CORREIOS_USER}:{settings.CORREIOS_SENHA}"
    basic = base64.b64encode(creds.encode()).decode()
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(settings.CORREIOS_TOKEN_URL, headers={"Authorization": f"Basic {basic}"})
        if r.status_code != 200:
            raise RuntimeError(f"Falha ao autenticar Correios: {r.status_code} {r.text[:300]}")
        data = r.json()
        token = data.get("token") or data.get("access_token") or data.get("accessToken")
        if not token:
            raise RuntimeError(f"Token não retornado: {data}")
        _token_cache["token"] = token
        _token_cache["exp"] = time.time() + 3500
        return token

def peso_taxavel(psObjeto_g: int, comp: int, larg: int, alt: int) -> int:
    cubado_kg = (comp * larg * alt) / 6000
    if cubado_kg <= 5:
        return psObjeto_g
    cubado_g = int(cubado_kg * 1000)
    return max(psObjeto_g, cubado_g)

def validar_dimensoes(comp: int, larg: int, alt: int):
    soma = comp + larg + alt
    if not (15 <= comp <= 100): raise ValueError("Comprimento deve ser 15-100cm")
    if not (10 <= larg <= 100): raise ValueError("Largura deve ser 10-100cm")
    if not (1 <= alt <= 100): raise ValueError("Altura deve ser 1-100cm")
    if not (29 <= soma <= 200): raise ValueError("Soma C+L+A deve ser 29-200cm")

async def calcular_frete(cepDestino: str, psObjeto: int, comp: int, larg: int, alt: int, tpObjeto: int = 2, vlDeclarado: Optional[float] = None, coProduto: Optional[str] = None):
    cepDestino = "".join(c for c in cepDestino if c.isdigit())
    cepOrigem = "".join(c for c in settings.CORREIOS_CEP_ORIGEM if c.isdigit())
    if len(cepDestino) != 8: raise ValueError("CEP destino deve ter 8 dígitos")
    if len(cepOrigem) != 8: raise ValueError("CEP origem inválido")
    validar_dimensoes(comp, larg, alt)
    taxavel = peso_taxavel(psObjeto, comp, larg, alt)
    token = await _get_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    # Preço e prazo em paralelo
    payload_preco = {
        "idLote": "1",
        "parametrosPrazo": [{
            "coProduto": coProduto or settings.CORREIOS_CO_PRODUTO_PAC,
            "cepOrigem": cepOrigem,
            "cepDestino": cepDestino,
            "psObjeto": str(taxavel),
            "tpObjeto": str(tpObjeto),
            "comprimento": str(comp),
            "largura": str(larg),
            "altura": str(alt),
            "diametro": "0",
        }]
    }
    if vlDeclarado: payload_preco["parametrosPrazo"][0]["vlDeclarado"] = vlDeclarado

    async with httpx.AsyncClient(timeout=15) as client:
        # prazo
        r_prazo = await client.post(settings.CORREIOS_PRAZO_URL, json=payload_preco, headers=headers)
        # preco - mesmo payload mas endpoint diferente
        r_preco = await client.post(settings.CORREIOS_PRECO_URL, json=payload_preco, headers=headers)
    if r_prazo.status_code != 200:
        raise RuntimeError(f"Erro prazo Correios: {r_prazo.status_code} {r_prazo.text[:500]}")
    if r_preco.status_code != 200:
        raise RuntimeError(f"Erro preco Correios: {r_preco.status_code} {r_preco.text[:500]}")
    return {
        "pesoTaxavel": taxavel,
        "pesoCubadoKg": round((comp*larg*alt)/6000,2),
        "prazo": r_prazo.json(),
        "preco": r_preco.json(),
    }
