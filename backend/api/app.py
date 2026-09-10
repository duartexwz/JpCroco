import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.database import ensure_pool
from api.routers import admins, cliente, consent, endereco, frete, itens_pedido, login, pagamento, pedidos, produtos, push, rastreio, upload, usuarios
from api.settings import settings

log = logging.getLogger('db')


@asynccontextmanager
async def lifespan(app: FastAPI):  # pragma: no cover
    # Eager quando possível, mas nunca derruba o startup no serverless:
    # o pool é criado sob demanda na primeira requisição (ensure_pool).
    try:
        app.state.pool = await ensure_pool(app)
    except Exception as e:
        log.warning('Pool DB adiado para primeira requisição: %s', str(e)[:200])
        app.state.pool = None
    yield

    if getattr(app.state, 'pool', None) is not None:
        await app.state.pool.close()


app = FastAPI(lifespan=lifespan)


@app.middleware('http')
async def strip_api_prefix(request, call_next):  # pragma: no cover
    """Remove o prefixo /api quando presente.

    No Docker o nginx já remove o prefixo no proxy_pass; na Vercel o
    rewrite encaminha o caminho cheio (/api/login/) ao backend, cujas
    rotas são registradas sem prefixo (/login/). Sem isso tudo dá 404.
    """
    path = request.scope.get('path', '')
    if path == '/api':
        request.scope['path'] = '/'
    elif path.startswith('/api/'):
        request.scope['path'] = path[4:]
    return await call_next(request)


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=['GET', 'POST', 'PATCH', 'DELETE'],
    allow_headers=['*'],
)

app.include_router(produtos.router)
app.include_router(login.router)
app.include_router(pedidos.router)
app.include_router(usuarios.router)
app.include_router(cliente.router)
app.include_router(pagamento.router)
app.include_router(pagamento.payments_router)
app.include_router(push.router)
app.include_router(itens_pedido.router)
app.include_router(upload.router)
app.include_router(admins.router)
app.include_router(rastreio.router)
app.include_router(frete.router)
app.include_router(endereco.router)
app.include_router(consent.router)


@app.get('/health', tags=['health'])
async def health_check():
    return {'status': 'ok'}

