from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.database import create_db_pool
from api.routers import admins, cliente, consent, endereco, frete, itens_pedido, login, pagamento, pedidos, produtos, push, rastreio, upload, usuarios
from api.settings import settings


@asynccontextmanager
async def lifespan(app: FastAPI):  # pragma: no cover
    app.state.pool = await create_db_pool()
    yield

    await app.state.pool.close()


app = FastAPI(lifespan=lifespan)


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

