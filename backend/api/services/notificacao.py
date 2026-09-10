import asyncio
import logging
from email.mime.text import MIMEText
import smtplib

import httpx

from api.settings import settings

log = logging.getLogger("notificacao")

def _msg_rastreio(nome: str, id_pedido: str, codigo: str, transportadora: str) -> str:
    return (
        f"Olá {nome or 'cliente'}! Seu pedido {id_pedido} foi enviado via {transportadora}.\n"
        f"Código de rastreio: {codigo}\n"
        f"Acompanhe em: {settings.FRONTEND_URL}/minhas-compras ou https://www2.correios.com.br/sistemas/rastreamento/\n"
        f"Entrega para todo o Brasil."
    )

async def enviar_email(destinatario: str, assunto: str, corpo: str):
    if not settings.SMTP_USER or not settings.SMTP_PASS:
        log.warning("SMTP não configurado, email não enviado para %s", destinatario)
        return
    try:
        msg = MIMEText(corpo)
        msg["Subject"] = assunto
        msg["From"] = settings.SMTP_FROM
        msg["To"] = destinatario
        # roda em thread para não bloquear
        def _send():
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as s:
                s.starttls()
                s.login(settings.SMTP_USER, settings.SMTP_PASS)
                s.send_message(msg)
        await asyncio.to_thread(_send)
        log.info("Email rastreio enviado para %s", destinatario)
    except Exception as e:
        log.error("Falha email rastreio %s: %s", destinatario, e)

async def enviar_whatsapp(telefone: str, mensagem: str):
    # Suporta UltraMsg/Z-API/Evolution via WHATSAPP_API_URL
    # Ex: WHATSAPP_API_URL=https://api.ultramsg.com/instanceID/messages/chat
    # Se não configurado, apenas loga (admin ainda pode usar wa.me manual)
    url = getattr(settings, "WHATSAPP_API_URL", "") or ""
    token = getattr(settings, "WHATSAPP_TOKEN", "") or ""
    if not url or not telefone:
        log.info("WhatsApp não configurado, mensagem logada: %s -> %s", telefone, mensagem[:80])
        return
    try:
        tel = "".join(c for c in telefone if c.isdigit())
        if not tel.startswith("55"): tel = "55" + tel
        payload = {"to": tel, "body": mensagem}
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        # tenta formatos comuns
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(url, json=payload, headers=headers)
            if r.status_code not in (200, 201):
                # tenta form x-www-form-urlencoded (UltraMsg)
                r2 = await client.post(url, data={"token": token, "to": tel, "body": mensagem})
                if r2.status_code not in (200, 201):
                    log.warning("WhatsApp falhou %s: %s %s", tel, r.status_code, r.text[:300])
                else:
                    log.info("WhatsApp enviado para %s", tel)
            else:
                log.info("WhatsApp enviado para %s", tel)
    except Exception as e:
        log.error("Falha WhatsApp %s: %s", telefone, e)

async def notificar_rastreio(cliente: dict, pedido: dict):
    nome = cliente.get("nome") or ""
    email = cliente.get("email")
    telefone = cliente.get("telefone")
    codigo = pedido.get("codigo_rastreio")
    id_pedido = pedido.get("id_pedido")
    transportadora = pedido.get("transportadora") or "Correios"
    if not codigo or not id_pedido:
        return
    msg = _msg_rastreio(nome, id_pedido, codigo, transportadora)
    # envia email + whatsapp em paralelo, sem bloquear o PATCH
    await asyncio.gather(
        enviar_email(email, f"Seu pedido {id_pedido} foi enviado!", msg) if email else asyncio.sleep(0),
        enviar_whatsapp(telefone, msg) if telefone else asyncio.sleep(0),
    )
