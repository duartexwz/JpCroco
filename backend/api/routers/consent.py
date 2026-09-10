from fastapi import APIRouter, Depends
import asyncpg
from api.database import get_db
from typing import Annotated

router = APIRouter(prefix='/consentimento', tags=['consentimento'])
dbConnection = Annotated[asyncpg.Connection, Depends(get_db)]

@router.post('')
async def salvar_consentimento(dados: dict, db: dbConnection):
    # dados: {necessarios, analiticos, marketing, aceitou, versao, data, ip}
    email = dados.get("email")
    cliente_id = None
    if email:
        row = await db.fetchrow("SELECT id FROM clientes WHERE email = $1", email)
        if row: cliente_id = row["id"]
    await db.execute(
        "INSERT INTO consentimentos (cliente_id, email, ip, versao, necessarios, analiticos, marketing, aceitou) VALUES ($1,$2,$3,$4,$5,$6,$7,$8)",
        cliente_id, dados.get("email"), dados.get("ip"), dados.get("versao","1.0"),
        dados.get("necessarios", True), dados.get("analiticos", False), dados.get("marketing", False), dados.get("aceitou", False)
    )
    return {"ok": True}
