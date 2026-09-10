"""Web Push (VAPID) para o aparelho do admin, mesmo com o site fechado.

O polling do painel só funciona com a página aberta. Este módulo permite
que o backend empurre a notificação via Push API do navegador (exige
contexto seguro: HTTPS/ngrok ou localhost).
"""
import asyncio
import json
import logging
from http import HTTPStatus
from typing import Annotated

import asyncpg
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from api.database import get_db
from api.security import get_current_admin
from api.settings import settings

router = APIRouter(prefix='/push', tags=['push'])
dbConnection = Annotated[asyncpg.Connection, Depends(get_db)]
AdminUser = Annotated[dict, Depends(get_current_admin)]

log = logging.getLogger('push')

CREATE_SQL = """
CREATE TABLE IF NOT EXISTS push_subscriptions (
    endpoint TEXT PRIMARY KEY,
    p256dh TEXT NOT NULL,
    auth TEXT NOT NULL,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


async def _ensure(db: asyncpg.Connection) -> None:
    await db.execute(CREATE_SQL)


@router.get('/vapid-key')
async def vapid_key():
    return {'public_key': settings.VAPID_PUBLIC_KEY}


@router.post('/subscribe', status_code=HTTPStatus.CREATED)
async def subscribe(sub: dict, db: dbConnection, admin: AdminUser):
    await _ensure(db)
    endpoint = (sub.get('endpoint') or '').strip()
    keys = sub.get('keys') or {}
    if not endpoint or not keys.get('p256dh') or not keys.get('auth'):
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail='Subscription inválida')
    await db.execute(
        """INSERT INTO push_subscriptions (endpoint, p256dh, auth)
           VALUES ($1, $2, $3)
           ON CONFLICT (endpoint) DO UPDATE SET p256dh = EXCLUDED.p256dh, auth = EXCLUDED.auth""",
        endpoint, keys['p256dh'], keys['auth'],
    )
    return {'ok': True}


@router.post('/unsubscribe')
async def unsubscribe(payload: dict, db: dbConnection, admin: AdminUser):
    await _ensure(db)
    endpoint = (payload.get('endpoint') or '').strip()
    if endpoint:
        await db.execute('DELETE FROM push_subscriptions WHERE endpoint = $1', endpoint)
    return {'ok': True}


async def _send_one(sub: dict, titulo: str, corpo: str) -> None:
    def _do():
        from pywebpush import webpush
        webpush(
            subscription_info={'endpoint': sub['endpoint'], 'keys': {'p256dh': sub['p256dh'], 'auth': sub['auth']}},
            data=json.dumps({'title': titulo, 'body': corpo}),
            vapid_private_key=settings.VAPID_PRIVATE_KEY,
            vapid_claims={'sub': settings.VAPID_SUBJECT},
        )

    try:
        await asyncio.to_thread(_do)
    except Exception as e:
        status = getattr(e, 'response', None).status_code if getattr(e, 'response', None) else None
        log.warning('Push falhou (%s): %s', status, str(e)[:200])
        # Subscription morta (404/410): remove para não tentar de novo
        if status in (404, 410):
            try:
                conn = await asyncpg.connect(settings.DATABASE_URL)
                try:
                    await conn.execute('DELETE FROM push_subscriptions WHERE endpoint = $1', sub['endpoint'])
                finally:
                    await conn.close()
            except Exception:
                pass


async def tarefa_push_admins(titulo: str, corpo: str) -> None:
    """BackgroundTask: empurra push para todos os aparelhos inscritos."""
    if not settings.VAPID_PRIVATE_KEY or not settings.VAPID_PUBLIC_KEY:
        return
    try:
        conn = await asyncpg.connect(settings.DATABASE_URL)
    except Exception as e:
        log.warning('Push: sem banco: %s', str(e)[:150])
        return
    try:
        try:
            await conn.execute(CREATE_SQL)
            rows = await conn.fetch('SELECT endpoint, p256dh, auth FROM push_subscriptions')
        finally:
            await conn.close()
    except Exception as e:
        log.warning('Push: erro lendo subscriptions: %s', str(e)[:150])
        return
    if not rows:
        return
    await asyncio.gather(*[_send_one(dict(r), titulo, corpo) for r in rows])


def agendar_push(background: BackgroundTasks, titulo: str, corpo: str) -> None:
    background.add_task(tarefa_push_admins, titulo, corpo)
