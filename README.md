# 🐊 JP Croco — Loja Online

Loja virtual completa de moda (tema Lacoste) com vitrine, sacola, checkout com cálculo de frete,
pagamento via **Mercado Pago (Brick)**, rastreio de entrega, área do cliente e painel administrativo
com **notificação no aparelho do admin** a cada mudança de status do pedido.

## Índice

1. [Visão geral](#1-visão-geral)
2. [Arquitetura e portas](#2-arquitetura-e-portas)
3. [Stack](#3-stack)
4. [Funcionalidades](#4-funcionalidades)
5. [Fluxo do pedido (compra → entrega)](#5-fluxo-do-pedido-compra--entrega)
6. [Rotas do frontend](#6-rotas-do-frontend)
7. [Endpoints do backend](#7-endpoints-do-backend)
8. [Variáveis de ambiente](#8-variáveis-de-ambiente)
9. [Como rodar com Docker](#9-como-rodar-com-docker)
10. [Como rodar local (dev)](#10-como-rodar-local-dev)
11. [Banco de dados e migrações](#11-banco-de-dados-e-migrações)
12. [Estrutura de pastas](#12-estrutura-de-pastas)
13. [Troubleshooting](#13-troubleshooting)

---

## 1. Visão geral

- **Frontend:** React 18 + Vite + React Router (SPA), tema verde Lacoste com dourado, 100% responsivo
  (desktop, tablet e mobile). Servido pelo Nginx, que também faz proxy de `/api/` e `/uploads/`
  para o backend.
- **Backend:** FastAPI (Python 3.13) com PostgreSQL (asyncpg), JWT (Argon2), upload de imagens,
  integração Mercado Pago, Correios (CWS), ViaCEP, e-mail (SMTP) e Web Push (VAPID).
- **Pagamento:** nunca toca no cartão — usa o **Payment Brick** do Mercado Pago (cartão, débito,
  boleto e **Pix com QR Code**) + webhook que confirma o pedido e dá baixa no estoque.
- **Entrega:** cálculo de frete por CEP (PAC/SEDEX via Correios ou simulação quando sem credencial;
  Retirada/Uber no DF e Entorno), endereço com autofill ViaCEP, código de rastreio lançado pelo
  admin com timeline em tempo real para o cliente.
- **Privacidade:** ao cliente **nunca é exibido o `#id` interno** do pedido — só o protocolo
  público (`id_pedido`); quando ainda não há protocolo, a UI mostra "Pedido em processamento".

## 2. Arquitetura e portas

```
Navegador ──► Nginx (frontend :8070)
                 ├── /  ──────────────► React build (dist/index.html, SPA)
                 ├── /api/* ──proxy───► FastAPI (backend :8055, strip do /api)
                 └── /uploads/* ─proxy► FastAPI (imagens dos produtos)
FastAPI ──► PostgreSQL :5433 (host) / 5432 (container)
FastAPI ──► Mercado Pago, Correios CWS, ViaCEP, SMTP, Push (VAPID)
```

| Serviço  | Container        | Porta host | Porta interna |
|----------|------------------|------------|---------------|
| Frontend | `frontend`       | 8070       | 8070          |
| Backend  | (compose `backend`) | 8055    | 8055          |
| Banco    | `loja_online_db` | 5433       | 5432          |

> O backend **sempre** recebe as rotas sem o prefixo `/api` (o Nginx remove). Todos os routers
> seguem esse padrão — inclusive `/payments/*` (ver [Troubleshooting](#13-troubleshooting)).

## 3. Stack

| Camada    | Tecnologias |
|-----------|-------------|
| Frontend  | React 18, React Router 6, Vite 5, CSS próprio (tema Lacoste), Mercado Pago JS SDK v2 (Brick) |
| Backend   | FastAPI, asyncpg, PyJWT, pwdlib (Argon2), mercadopago SDK, pywebpush, httpx, fastapi-mail |
| Banco     | PostgreSQL 16 |
| Infra     | Docker + Compose, Nginx (SPA + proxy), Gunicorn/Uvicorn (alternativo) |

## 4. Funcionalidades

### Vitrine e sacola
- Home com hero, destaques, história da marca e CTA; Loja com **filtros por tamanho + busca**.
- Cards com foto, promo (preço riscado), estoque e tag Esgotado/Promo; modal de detalhe com
  galeria, escolha de tamanho e quantidade.
- Sacola lateral (drawer) persistida por aba (`sessionStorage`), controle de quantidade
  respeitando o estoque por tamanho.

### Conta e login
- Cadastro/login com e-mail + senha (JWT por aba — permite 2 contas em 2 abas), "esqueci senha"
  com link por e-mail (`/redefinir-senha?token=...`), Minha Conta com dados pessoais
  (nome, e-mail, telefone, CPF) **obrigatórios para comprar** — o checkout reaproveita esses dados.

### Checkout e frete (entrega)
- Endereço com **máscara de CEP + autofill ViaCEP** (rua/cidade/UF).
- **Cálculo de frete por CEP** considerando peso real, peso cubado e dimensões do carrinho:
  - DF e Entorno (CEPs 70/71/72/73): **Retirada no local (grátis)** ou **Uber Delivery (a combinar)**;
  - Resto do Brasil: **PAC e SEDEX** (valores/prazos reais via Correios CWS ou simulação
    quando `CORREIOS_USER/SENHA` não configurados — indicado na tela como "simulação").
- O pedido grava `valor_total`, `valor_frete`, `subtotal`, `cep_destino` e `entrega_tipo`.

### Pagamento (Mercado Pago)
- Modal segura com **Payment Brick**: cartão de crédito/débito, boleto e **Pix com QR Code
  + copia-e-cola**.
- Processamento em `POST /payments/process` com `X-Idempotency-Key` (sem dupla cobrança);
  aprovado → pedido vira `Pago` + **baixa automática no estoque** (produto e tamanho);
  em análise → aviso; recusado → motivo traduzido (ex.: "Saldo ou limite insuficiente").
- **Webhook** (`POST /webhook/mercadopago`, com validação HMAC) confirma o pagamento mesmo com
  o site fechado e notifica o admin.

### Minhas Compras (cliente)
- Lista com filtro por status, itens com foto, subtotal/frete/total, endereço e CEP.
- **Rastreio em tempo real**: stepper Postado → Em Trânsito → Saiu p/ Entrega → Entregue +
  timeline de eventos (Correios, com fallback para o status local).
- Entrega local: botão WhatsApp contextual (solicitar endereço da loja / chamar vendedor).

### Painel Admin
- Dashboard (totais + receita + recentes), CRUD de **produtos** (preço/promo, tamanhos+estoque,
  upload de imagens com capa), **pedidos** (abas por status, busca, exclusão),
  usuários/clientes/admins.
- **Gerenciar entrega**: alterar status, lançar **código de rastreio + transportadora**
  (vira `Enviado` e **notifica o cliente** por e-mail/WhatsApp); validação de rastreio
  (mín. 8 chars) e de fluxo (só marca `Entregue` após envio/pagamento).
- **🔔 Notificação no aparelho do admin logado**: a cada mudança de status do pedido o admin
  recebe **toast no painel + notificação do sistema no aparelho** (som, vibração, título
  piscando). Com Handlers: Service Worker (`/sw.js`) + inscrição Web Push (`/push/subscribe`,
  exige login admin) → chega **mesmo com o site fechado** (requer HTTPS e chaves VAPID).
  Barra no topo do painel mostra o estado e permite Ativar/Pausar. Polling de 15s cobre a
  página aberta; o push do backend cobre os demais aparelhos/sessões.

## 5. Fluxo do pedido (compra → entrega)

1. Cliente monta a sacola → **Finalizar Compra** (exige login + dados pessoais completos).
2. Informa CEP → endereço preenche via ViaCEP → **calcula frete** → escolhe a entrega.
3. **Confirmar** cria o pedido `pendente` + itens (protocolo oculto até o pagamento).
4. Modal de pagamento (Brick) → Pix/cartão/boleto → aprovado: pedido `Pago` + baixa de estoque.
5. Admin vê a venda (painel + aparelho) → separa → lança **código de rastreio** → `Enviado`
   (cliente notificado) → cliente acompanha a timeline → admin marca `Entregue`.

Status possíveis: `pendente` → `Pago` → `Enviado` → `Entregue` (ou `Recusado`/`Cancelado`).

## 6. Rotas do frontend

| Rota | Acesso | Descrição |
|------|--------|-----------|
| `/` | público | Home (retorno do MP: `?collection_status=`/`status=` mostra toast) |
| `/loja` | público | Vitrine completa com filtros e busca |
| `/login` | público | Entrar / criar conta / esqueci senha |
| `/redefinir-senha?token=` | público | Definir nova senha |
| `/conta` | logado | Dados pessoais e segurança |
| `/minhas-compras` | logado | Pedidos, frete, rastreio, WhatsApp |
| `/admin` | admin | Painel completo + notificações do aparelho |
| `/politica-privacidade` | público | LGPD |

## 7. Endpoints do backend

Base: `/api/` no navegador (sem `/api` dentro do container).

| Método | Endpoint | Auth | Descrição |
|--------|----------|------|-----------|
| POST | `/login/` | — | Login (form `username`+`password` → JWT) |
| POST | `/login/esqueci-senha` | — | Envia link de reset |
| POST | `/login/redefinir-senha` | — | Troca a senha com token |
| GET | `/produtos/` | — | Lista (filtros: nome, preço, tamanho, estoque) |
| POST/PATCH/DELETE | `/produtos/` | admin | CRUD de produtos (+tamanhos/imagens) |
| GET/POST/PATCH | `/clientes/` | logado | Dados do cliente (checkout/conta) |
| POST | `/pedidos/` | logado | Cria pedido (protocolo oculto se pendente) |
| GET | `/pedidos/meus` | logado | Pedidos do e-mail logado |
| GET | `/pedidos/` | logado | Lista/filtra (admin vê todos) |
| PATCH | `/pedidos/{id_pedido}` | logado | Atualiza status/rastreio/frete (**dispara push ao admin**) |
| POST | `/itens_pedido/` | logado | Adiciona item (com `tamanho`) |
| POST | `/frete/calcular` | — | `{cepDestino, itens}` → `opcoes[]` normalizadas |
| GET | `/endereco/cep/{cep}` | — | ViaCEP normalizado (rua/bairro/cidade/estado) |
| GET | `/rastreio/{codigo}` | — | Correios (Link/Proxy) + fallback local com steps |
| GET | `/webhook/public-key` | — | Public Key do MP (Brick) |
| POST | `/payments/process` | logado | Processa Brick (idempotente) |
| POST | `/webhook/mercadopago` | MP | Webhook (HMAC) → `Pago` + estoque + push |
| GET | `/push/vapid-key` | — | Chave VAPID pública |
| POST/POST | `/push/subscribe`, `/push/unsubscribe` | admin | Inscrição do aparelho |
| POST | `/upload/imagem` | admin | Upload (JPG/PNG/WebP ≤ 5 MB) |
| GET | `/health` | — | Health check |

## 8. Variáveis de ambiente

### Backend (`backend/.env` — ver `.env.example`)
Obrigatórias: `DATABASE_URL`, `SECRET_KEY` (64+ chars), `ALGORITHM`, `MERCADOPAGO_ACCESS_TOKEN`,
`MERCADOPAGO_WEBHOOK_SECRET`, `FRONTEND_URL` (HTTPS em produção, sem path), `CORS_ORIGINS`.
Pagamento: `MERCADOPAGO_PUBLIC_KEY` (`TEST-`/`APP_USR-`), `WEBHOOK_URL` (ex.: ngrok `.../api/webhook/mercadopago`).
Entrega: `CORREIOS_USER`, `CORREIOS_SENHA`, `CORREIOS_CEP_ORIGEM` (sem credencial → simulação avisada na tela).
Notificações: `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`, `VAPID_SUBJECT`, `VENDEDOR_WHATSAPP`.
E-mail: `SMTP_HOST/PORT/USER/PASS/FROM` (Gmail usa senha de app).

### Frontend (`frontend/.env` — ver `.env.example`)
`VITE_API_URL` (`/api` no Docker; URL do backend em dev), `VITE_VENDEDOR_WHATSAPP`.

## 9. Como rodar com Docker

```bash
cp backend/.env.example backend/.env   # preencher (seção 8)
cp frontend/.env.example frontend/.env # opcional (padrões já servem no Docker)
docker compose up -d --build
docker compose exec backend python migrate.py up      # aplica backend/migrations/
docker compose exec backend python migrate.py status  # confere
```

Acesse: frontend `http://localhost:8070` • API `http://localhost:8055/health`.
Criar admin inicial e logs: ver `DEPLOY.md` (procedimento original mantido).

> O `Dockerfile` do backend copia `api/`, `migrations/`, `migrate.py` e `schema.sql`,
> e o do frontend faz build do React (Node 20) e serve o `dist/` no Nginx com fallback SPA.

## 10. Como rodar local (dev)

```bash
# Backend
cd backend && poetry install && cp .env.example .env
poetry run fastapi dev api/app.py        # http://localhost:8000 (ajuste o VITE_API_URL)

# Frontend
cd frontend && npm install && npm run dev # http://localhost:5173 (proxy /api e /uploads)
```

## 11. Banco de dados e migrações

- `backend/migrate.py up|status|down` + SQL versionado em `backend/migrations/`
  (`002_entrega.sql`: colunas de frete/rastreio em `pedidos`, `tamanho` em `itens_pedido`,
  tabelas `produto_tamanhos`, `produto_imagens`, `push_subscriptions` — idempotente).
- O código tem fallback para bancos antigos sem as colunas de frete.
- Tabelas principais: `usuarios`, `admins`, `clientes`, `produtos`, `produto_tamanhos`,
  `produto_imagens`, `pedidos`, `itens_pedido`, `push_subscriptions`, `schema_migrations`.

## 12. Estrutura de pastas

```
loja-online/
├── README.md                  # este arquivo
├── DEPLOY.md                  # guia original de deploy
├── docker-compose.yml         # frontend :8070, backend :8055, postgres :5433
├── frontend/
│   ├── Dockerfile             # build React (Node 20) → Nginx (dist)
│   ├── nginx.conf             # SPA + proxy /api/ e /uploads/
│   ├── vite.config.js         # dev proxy p/ o backend local
│   ├── public/sw.js           # push no aparelho do admin
│   └── src/
│       ├── api/client.js      # HTTP + frete/CEP/rastreio/pagamento (+protocoloPedido)
│       ├── store/             # AuthContext, CartContext, ToastContext
│       ├── hooks/useAdminNotify.js  # permissão, SW, VAPID, som/vibração
│       ├── components/        # Header, Footer, ProductCard/Modal, CartDrawer,
│       │                      # CheckoutModal (CEP+frete), PaymentModal (Brick+Pix), Tracking
│       └── pages/             # Home, Loja, Login, Conta, MinhasCompras, Admin, ...
└── backend/
    ├── Dockerfile             # Python 3.13 + poetry (+migrations p/ migrate.py)
    ├── migrate.py + migrations/
    └── api/
        ├── app.py             # FastAPI + CORS + routers
        ├── routers/           # login, usuarios, admins, produtos, cliente,
        │                      # pedidos, itens_pedido, pagamento (/webhook+/payments),
        │                      # frete, endereco, rastreio, push, upload, consent
        └── services/          # correios (CWS), notificacao (e-mail/WhatsApp)
```

## 13. Troubleshooting

- **`POST /payments/process` 404:** o backend espera o path **sem** `/api`
  (o Nginx remove). O router é `/payments` — não use `/api/payments` em chamadas internas.
- **Brick não carrega / "Public Key não configurada":** confira `MERCADOPAGO_PUBLIC_KEY`
  no `.env` do backend (`GET /webhook/public-key` deve retornar `TEST-`/`APP_USR-`); AdBlock
  pode bloquear o SDK (`sdk.mercadopago.com/js/v2`).
- **Pagamento recusado:** o toast traduz o `status_detail` (ex.: saldo insuficiente) — tente
  outro cartão ou o Pix.
- **Frete sempre "simulação":** configure `CORREIOS_USER/SENHA`; sem eles o cálculo usa a
  fórmula local e avisa na tela.
- **Push no aparelho não chega com site fechado:** exige HTTPS (ou localhost) + VAPID
  configurado + permissão concedida; a barra 🔔 do painel informa o motivo. Com a página
  aberta, o polling de 15s + som/vibração cobrem.
- **CORS:** inclua a origem do frontend em `CORS_ORIGINS`.
- **E-mail não envia:** Gmail exige senha de app; sem SMTP o pedido segue e o log avisa.
