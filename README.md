# 🐊 JP Croco — Loja Online

Loja virtual completa de moda com vitrine, sacola por usuário, checkout com frete real,
pagamento **Mercado Pago (Pix com confirmação automática)**, rastreio, área do cliente e
painel admin com **push no aparelho**, etiqueta de envio e pop-up do pedido mais recente.

> **Produção:** https://jpcroco.vercel.app (frontend + backend no mesmo domínio)

## Índice

1. [Visão geral](#1-visão-geral)
2. [Arquitetura](#2-arquitetura)
3. [Stack](#3-stack)
4. [Funcionalidades](#4-funcionalidades)
5. [Fluxo do pedido (compra → entrega)](#5-fluxo-do-pedido-compra--entrega)
6. [Rotas do frontend](#6-rotas-do-frontend)
7. [Endpoints do backend](#7-endpoints-do-backend)
8. [Variáveis de ambiente](#8-variáveis-de-ambiente)
9. [Como rodar com Docker (dev local)](#9-como-rodar-com-docker-dev-local)
10. [Como rodar local sem Docker](#10-como-rodar-local-sem-docker)
11. [Banco de dados e migrações](#11-banco-de-dados-e-migrações)
12. [Estrutura de pastas](#12-estrutura-de-pastas)
13. [Roadmap: refatoração e organização](#13-roadmap-refatoração-e-organização)
14. [Troubleshooting](#14-troubleshooting)
15. [Antes de deixar o repo público](#15-antes-de-deixar-o-repo-público)

---

## 1. Visão geral

- **Frontend:** React 18 + Vite + React Router em modo **Hash** (`/#/loja` — funciona com F5 em
  qualquer hospedagem estática, sem depender de rewrites do servidor). Tema verde Lacoste com
  dourado, responsivo (desktop/tablet/mobile). Code-split por rota + `SafeImg` (fallback 🐊
  quando a foto quebra).
- **Backend:** FastAPI (Python 3.13) + PostgreSQL **Neon** (asyncpg, **1 conexão dedicada por
  requisição** — sem pool compartilhado, à prova de troca de event loop no serverless),
  JWT com **renovação silenciosa** (grace de 7 dias), Argon2, Mercado Pago, frete
  **SuperFrete** (Melhor Envio de fallback), ViaCEP, SMTP e Web Push (VAPID).
- **Imagens:** upload múltiplo direto para o **Vercel Blob** (store **público**); stores privados
  retornam 403 no `<img>` — ver Troubleshooting.
- **Pagamento:** Payment Brick do Mercado Pago (cartão, débito, boleto e **Pix com QR Code**).
  Pix **in_process/pending** é confirmado por **polling** (`GET /payments/status/{id}`, 5s por
  até 10 min) além do webhook — aprovar no banco vira `Pago` em segundos, mesmo se o webhook
  falhar. Webhook com validação HMAC confirma com o site fechado e dá baixa no estoque.
- **Entrega:** cálculo por CEP (SuperFrete → PAC/SEDEX/Jadlog; Retirada/Uber no DF e Entorno),
  endereço com bairro + autofill ViaCEP, **etiqueta comprada no painel admin** (Melhor Envio,
  debita a carteira), rastreio lançado automaticamente com aviso ao cliente.
- **Privacidade:** ao cliente **nunca é exibido o `#id` interno** — só o protocolo público
  (`id_pedido`); sem protocolo, a UI mostra "Pedido em processamento".

## 2. Arquitetura

```
Navegador ──► Vercel (jpcroco.vercel.app, região gru1)
                 ├── /api/* ──► FastAPI serverless (backend/, entrypoint api.app:app)
                 └── /* ──────► Frontend estático (frontend/dist, HashRouter)
FastAPI ──► Neon Postgres (pooler pgbouncer p/ API; direto p/ DDL)
FastAPI ──► Mercado Pago, SuperFrete/Melhor Envio, Vercel Blob, ViaCEP, SMTP, Push (VAPID)
```

Desenvolvimento local alternativo com Docker (ver seção 9):

```
Navegador ──► Nginx (frontend :8070)
                ├── / ───────────► React build (SPA)
                ├── /api/* ─proxy► FastAPI (:8055, com strip do /api via middleware)
                └── /uploads/* ───► (legado local; produção usa Blob)
FastAPI ──► PostgreSQL :5433 (host) / 5432 (container)
```

> O backend aceita as rotas **com ou sem** o prefixo `/api` (middleware `strip_api_prefix`):
> no Docker o Nginx remove; na Vercel o rewrite encaminha o caminho cheio.

## 3. Stack

| Camada    | Tecnologias |
|-----------|-------------|
| Frontend  | React 18, React Router 6 (hash), Vite 5, CSS próprio, MP JS SDK v2 (Brick) |
| Backend   | FastAPI, asyncpg, PyJWT, pwdlib (Argon2), mercadopago SDK, pywebpush, httpx, fastapi-mail |
| Banco     | PostgreSQL 16 (Neon; Docker local opcional) |
| Infra     | Vercel (services frontend+backend, `vercel.json`), Docker + Compose (dev), Nginx (dev) |

## 4. Funcionalidades

### Vitrine e sacola
- Home com hero (foto da marca), destaques, história e CTA; Loja com **filtros por tamanho + busca**.
- Cards com foto, promo, estoque e tags; modal de detalhe com **foto inteira sem corte**, galeria,
  escolha de **cor → tamanhos da cor** e quantidade.
- **Sacola por usuário logado** (`carrinho:<username>`): trocar de conta não mistura sacolas; ao
  logar, o que estava na sacola anônima é mesclado. Logout nunca apaga a sacola de outra conta.

### Produtos (modelagem)
- `produtos`: nome, preço/promo, `cor` (principal), imagem de capa + `produto_imagens[]`.
- **Variantes cor × tamanho** em `produto_tamanhos` (`tamanho`, `stock`, `preco`, `cor`):
  ex. Verde/P, Verde/M, Preto/M. UNIQUE em `(produto_id, tamanho, cor)` + validação 400.
- Admin: múltiplas imagens (upload em lote p/ Blob, capa = primeira), cor por linha de tamanho,
  `Único` como opção de tamanho.

### Conta e login
- Cadastro/login com e-mail + senha; "esqueci senha" com link por e-mail.
- Sessão com **refresh silencioso**: 401 renova o token (janela de 7 dias) e repete a chamada —
  só desloga após 7 dias sem uso. Minha Conta exige dados completos para comprar.

### Checkout e frete
- Endereço com máscara de CEP + autofill ViaCEP (**com bairro**), formato versionado
  (`..., Bairro, Cidade - UF, CEP:`) lido pelo gerador de etiqueta.
- **Cálculo por CEP** (peso real + cubado + dimensões): DF/Entorno → Retirada/Uber;
  resto do Brasil → **SuperFrete** (fallback Melhor Envio). Sem provedor → 502 explícito
  (sem chute de preço).
- O pedido grava `valor_total`, `valor_frete`, `subtotal`, `cep_destino`, `entrega_tipo`.

### Pagamento (Mercado Pago)
- Modal com Brick + **Pix com QR + polling automático** e botão *"Já paguei — verificar agora"*.
- `POST /payments/process` idempotente; aprovado → `Pago` + baixa de estoque + **push ao admin**.
- `GET /payments/status/{payment_id}` confirma via consulta oficial (cobre falha de webhook).
- Webhook HMAC → mesmo efeito com o site fechado. Recusas traduzidas para o cliente.

### Minhas Compras (cliente)
- Filtro por status, itens com foto **e cor/tamanho**, frete/total, endereço e CEP.
- **Rastreio em tempo real** (stepper + timeline, com fallback local) + WhatsApp contextual.

### Painel Admin
- Dashboard, CRUD de produtos, pedidos (abas/busca/exclusão), usuários/clientes/admins.
- **Gerenciar entrega**: status, rastreio manual + transportadora, ou **etiqueta Melhor Envio**
  (PAC/SEDEX/Jadlog — cobra a carteira, salva o rastreio, marca `Enviado`, imprime e avisa).
- **Pop-up do pedido mais recente** ao entrar (1x por sessão, com som) + botão de gerenciar.
- Confirmações de exclusão em modal estilizada (sem `confirm()` nativo).
- **🔔 Aparelho do admin**: toast + notificação do sistema (som, vibração, título piscando) a
  cada evento; push VAPID chega **com o site fechado** (HTTPS + permissão + *Ativar aparelho*).

## 5. Fluxo do pedido (compra → entrega)

1. Sacola → **Finalizar Compra** (login + dados completos) → CEP → frete → entrega.
2. **Confirmar** cria o pedido `pendente` + itens (com `tamanho` e `cor`).
3. Pagamento (Brick/Pix) → polling confirma → `Pago` + baixa de estoque + push ao admin.
4. Admin gera a **etiqueta** (ou lança rastreio manual) → `Enviado` (cliente avisado).
5. Cliente acompanha a timeline → admin marca `Entregue`.

Status: `pendente` → `Pago` → `Enviado` → `Entregue` (ou `Recusado`/`Cancelado`).

## 6. Rotas do frontend

HashRouter — tudo após `/#/` (F5 sempre volta 200):

| Rota | Acesso | Descrição |
|------|--------|-----------|
| `/` | público | Home (retorno do MP via query mostra toast) |
| `/loja` | público | Vitrine com filtros e busca |
| `/login` | público | Entrar / criar conta / esqueci senha |
| `/redefinir-senha?token=` | público | Nova senha |
| `/conta` | logado | Dados pessoais e segurança |
| `/minhas-compras` | logado | Pedidos, frete, rastreio, WhatsApp |
| `/admin` | admin | Painel + pop-up do último pedido + aparelho |
| `/politica-privacidade` | público | LGPD |

## 7. Endpoints do backend

Base `/api/` (o backend aceita com ou sem o prefixo).

| Método | Endpoint | Auth | Descrição |
|--------|----------|------|-----------|
| POST | `/login/` | — | Login (form → JWT) |
| POST | `/login/refresh` | — | Renova token expirado (janela 7 dias) |
| POST | `/login/esqueci-senha` | — | Link de reset |
| POST | `/login/redefinir-senha` | — | Troca a senha |
| GET | `/produtos/` | — | Lista em lote (tamanhos/imagens, filtros) |
| POST/PATCH/DELETE | `/produtos/` | admin | CRUD (+variantes, valida repetido) |
| GET/POST/PATCH | `/clientes/` | logado | Dados do cliente |
| POST | `/pedidos/` | logado | Cria pedido (protocolo oculto se pendente) |
| GET | `/pedidos/meus` | logado | Pedidos do e-mail logado |
| GET | `/pedidos/` | logado | Lista/filtra (admin vê todos) |
| PATCH | `/pedidos/{id_pedido}` | logado | Status/rastreio (**push ao admin**) |
| POST | `/itens_pedido/` | logado | Item (com `tamanho` e `cor`) |
| POST | `/frete/calcular` | — | `{cepDestino, itens}` → `opcoes[]` (SuperFrete→ME) |
| POST | `/frete/etiqueta/{id}` | admin | Compra etiqueta ME (**cobra carteira**), rastreio+`Enviado` |
| GET | `/frete/oauth/url` | admin | URL de autorização OAuth do ME |
| GET | `/frete/oauth/callback` | — | Troca `code` por tokens (salva no banco) |
| POST | `/frete/melhorenvio-webhook` | ME | Eventos de tracking (log) |
| GET | `/endereco/cep/{cep}` | — | ViaCEP normalizado |
| GET | `/rastreio/{codigo}` | — | Tracking + fallback local com steps |
| GET | `/webhook/public-key` | — | Public Key do MP (Brick) |
| POST | `/payments/process` | logado | Brick idempotente |
| GET | `/payments/status/{id}` | logado | Consulta oficial (polling do Pix) |
| POST | `/webhook/mercadopago` | MP | Webhook HMAC → `Pago` + estoque + push |
| GET | `/push/vapid-key` | — | Chave VAPID pública |
| POST | `/push/subscribe`, `/push/unsubscribe` | admin | Aparelho |
| POST | `/upload/imagem` | admin | 1–8 imagens p/ Blob (502 com motivo se falhar) |
| GET | `/health` | — | Health check |

## 8. Variáveis de ambiente

`.env` raiz (Docker) **e** dashboard da Vercel (produção — redeploy após mudar).

| Grupo | Variáveis |
|-------|-----------|
| Banco | `DATABASE_URL` (pooler p/ API), `DATABASE_URL_UNPOOLED` (DDL) |
| Auth | `SECRET_KEY` (64+ chars), `ALGORITHM=HS256`, `ACCESS_TOKEN_EXPIRE_MINUTES=30` |
| Pagamento | `MERCADOPAGO_ACCESS_TOKEN` (`APP_USR-`), `MERCADOPAGO_PUBLIC_KEY`, `MERCADOPAGO_WEBHOOK_SECRET`, `WEBHOOK_URL=https://SEU_DOMINIO/api/webhook/mercadopago`, `FRONTEND_URL` (HTTPS, sem path) |
| Frete | `SUPERFRETE_TOKEN/API_URL/EMAIL/SERVICES`, `MELHORENVIO_TOKEN/CLIENT_ID/CLIENT_SECRET/REDIRECT_URI/API_URL/EMAIL/SERVICES`, `MELHORENVIO_FROM_*` (remetente, 11 vars), `CEP_ORIGEM` |
| Upload | `BLOB_READ_WRITE_TOKEN` (**store PÚBLICO** do Vercel Blob) |
| Push | `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`, `VAPID_SUBJECT` |
| E-mail | `SMTP_HOST/PORT/USER/PASS/FROM` (Gmail: senha de app) |
| Diversos | `CORS_ORIGINS`, `WHATSAPP_API_URL/TOKEN` (opcional), `CLIENTE_*` n/a (removidas `CLIENT_ID/SECRET`, `VENDEDOR_WHATSAPP`, `CORREIOS_*`) |

Templates: `backend/.env.example`, `frontend/.env.example`, `db.env.example`. **`.env` nunca entra no git.**

## 9. Como rodar com Docker (dev local)

```bash
cp backend/.env.example .env        # preencher (seção 8); ou edite o .env raiz
cp db.env.example db.env            # senha local
# cp frontend/.env.example frontend/.env  # opcional
docker compose up -d --build
docker compose exec backend python migrate.py up
docker compose exec backend python migrate.py status
```

Acesse: frontend `http://localhost:8070` • API `http://localhost:8055/health`.

Criar admin inicial (hash Argon2):

```bash
docker compose exec backend python -c "
import asyncio, asyncpg
from api.security import get_password_hash
async def main():
    c = await asyncpg.connect('postgresql://loja_admin:SUASENHA@db:5432/loja_online')
    await c.execute('''INSERT INTO admins (username, password, acesso, nome_completo)
      VALUES (\$1, \$2, 'admin', 'Administrador') ON CONFLICT (username) DO NOTHING''',
      'admin@loja.com', get_password_hash('troque-esta-senha'))
    await c.close()
asyncio.run(main())"
```

## 10. Como rodar local sem Docker

```bash
cd backend && poetry install && cp .env.example ../.env  # ajuste DATABASE_URL p/ Neon ou local
poetry run fastapi dev api/app.py        # http://localhost:8000
cd ../frontend && npm install && npm run dev  # http://localhost:5173 (proxy /api)
```

Testes/lint backend: `poetry run ruff check api/` (+ `ruff format --check`).

## 11. Banco de dados e migrações

- Produção: **Neon** (schema aplicado via `schema.sql`; dados via dump sem `OWNER`).
- `schema.sql` (raiz e `backend/`, sincronizados) = dump `--schema-only` canônico: 11 tabelas
  (`admins`, `clientes`, `consentimentos`, `itens_pedido` (+`cor`), `pedidos`, `produto_imagens`,
  `produto_tamanhos` (+`cor`, UNIQUE em `(produto_id,tamanho,cor)`), `produtos` (+`cor`),
  `schema_migrations`, `usuarios`, `melhorenvio_tokens`, `push_subscriptions` via DDL runtime).
- `backend/migrate.py up|status|down` + `backend/migrations/002_entrega.sql` (idempotente).
- `push_subscriptions` é criada em runtime (`CREATE TABLE IF NOT EXISTS`).

## 12. Estrutura de pastas

```
JpCroco/                      # (repo; deploy branch -> Vercel)
├── vercel.json               # services frontend/backend, regions gru1, rewrites /api
├── README.md / DEPLOY.md
├── .env / db.env             # LOCAIS, fora do git (.env.example / db.env.example no git)
├── schema.sql                # dump canônico (espelho de backend/schema.sql)
├── docker-compose.yml        # dev local: frontend :8070, backend :8055, pg :5433
├── frontend/
│   ├── Dockerfile / nginx.conf / vite.config.js
│   ├── index.html / public/ (sw.js push, favicon, marca) / dist/ (build, fora do git)
│   └── src/
│       ├── api/client.js     # HTTP + refresh silencioso + frete/CEP/rastreio/pagamento
│       ├── store/            # AuthContext, CartContext (por usuário), ToastContext
│       ├── hooks/useAdminNotify.js  # permissão, SW, VAPID, som/vibração/título
│       ├── components/       # Header, Footer, ProductCard/Modal, SafeImg, ConfirmModal,
│       │                     # CartDrawer, CheckoutModal (+bairro), PaymentModal (polling Pix)
│       └── pages/            # Home, Loja, Login, Conta, MinhasCompras, Admin (+pop-up),
│                             # RedefinirSenha, Politica
└── backend/
    ├── Dockerfile / migrate.py / migrations/ / schema.sql
    └── api/
        ├── app.py            # FastAPI + CORS + strip /api + lifespan sem pool
        ├── database.py       # 1 conexão por requisição (serverless-safe) + kwargs Neon
        ├── settings.py / security.py (JWT+Argon2, refresh 7 dias)
        ├── routers/          # login, usuarios, admins, produtos, cliente, pedidos,
        │                     # itens_pedido, pagamento (/webhook+/payments), frete
        │                     # (+etiqueta, oauth, webhook ME), endereco, rastreio,
        │                     # push, upload (Blob), consent
        ├── services/         # superfrete, melhorenvio (+OAuth/tokens), notificacao
        └── schemas/          # pydantic por recurso
```

## 13. Roadmap: refatoração e organização

> Aviso de direção — itens planejados, ainda não executados:

1. **Organização de pastas**: separar `docs/` (manuais), `scripts/` (seed/admin/dev), `infra/`
   (compose, nginx, vercel); mover `schema.sql` da raiz para `db/` ou `infra/`; avaliar
   remover o espelho duplicado (`backend/schema.sql` × `schema.sql`).
2. **Migrações como fonte única**: gerar `003_*.sql` (cores, OAuth ME, tokens) e aposentar
   edição manual do `schema.sql`; `migrate.py down` real (rollback, não só marcação).
3. **Testes**: suíte `pytest` (routers críticos: pagamento, frete, auth) + CI no push.
4. **Frontend**: extrair `api/` por domínio, hook `usePedidos` no admin (Arquivo Admin.jsx grande),
   e2e do checkout com Playwright.
5. **Pagamentos**: conciliação periódica (job varre `pendente` antigos via `/payments/status`).
6. **Frete**: rastreio automático SuperFrete + reimpressão de etiqueta pelo painel.

## 14. Troubleshooting

- **F5 em rota dá 404:** usamos HashRouter (`/#/admin`) — qualquer 404 em rota indica URL sem `#`
  ou deploy antigo. Links internos usam `<Link>`; `window.location` cruas usam `/#/`.
- **`/frete/calcular` 502 "token não configurado":** falta `SUPERFRETE_TOKEN` (ou ME) no ambiente.
  Sem provedor não há chute de preço — configure e redeploye (env exige redeploy).
- **Upload 502 com motivo do Blob:** store **privado** dá 400/403 — imagens de vitrine exigem
  Blob store **público**; o endpoint valida legibilidade e explica.
- **Pix não confirma:** polling cobre webhook perdido; `GET /payments/status/{id}` diz o estado
  oficial. Pedidos `pendente` antigos não viram `Pago` sozinhos (webhook é event-driven).
- **Push sem site fechado:** HTTPS + VAPID + permissão + *Ativar aparelho*; barra 🔔 diagnostica.
- **Sessão cai:** só após 7 dias sem uso; antes disso o refresh silencioso renova.
- **Tela branca após pagar:** era o `unmount()` do Brick (corrigido com `desmontarBrick()`).
- ** `jwt` x `PyJWT`:** nunca instale o pacote `jwt` (sombra o PyJWT e quebra `DecodeError`).
- **CORS:** origem do frontend em `CORS_ORIGINS`. **E-mail:** Gmail usa senha de app.
- **Foto cortada na modal:** `object-fit: contain` + `display:block` (grid centralizado
  transbordava); cards mantêm `cover` de propósito.

## 15. Antes de deixar o repo público

- [x] `.env`, `db.env`, dumps e hashes fora do git (`.gitignore` + `rm --cached`); só `*.example` versionados.
- [ ] **Girar segredos que já passaram pelo histórico do git**: `SECRET_KEY`, senha do Postgres
  local, tokens MP, VAPID, SMTP, Blob, Melhor Envio/SuperFrete, `WHATSAPP_TOKEN`. O `git rm`
  não apaga o passado — sem rotação, o histórico expõe tudo.
- [ ] Opcional: reescrever histórico (`git filter-repo`) ou squash público; e remover
  `node_modules/` e `Page.tsx`/`Logo.jpeg` pendentes conforme decisão.
- [ ] Preencher `MELHORENVIO_FROM_*` reais e `SUPERFRETE_*` de produção **só no dashboard**
  da Vercel, nunca em arquivo.
