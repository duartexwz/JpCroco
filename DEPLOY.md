# Deploy - JP Croco

Guia de deploy em produção (**Vercel**) e desenvolvimento local (Docker).

## Produção (Vercel — método oficial)

Arquitetura: monorepo com `vercel.json` (`services: frontend + backend`, `regions: ["gru1"]`).

```
Navegador ──► jpcroco.vercel.app
                 ├── /api/* ──► FastAPI serverless (backend/, api.app:app)
                 └── /* ──────► frontend/dist (HashRouter: /#/loja, F5 sempre 200)
```

### 1. Conectar o repo

Vercel → *Add New Project* → repositório → Root Directory = raiz → Production Branch = `deploy`.
O build detecta os services sozinho (`frontend/` Vite, `backend/` Python).

### 2. Environment Variables (Production)

Todas em *Settings → Environment Variables*. **Redeploy após qualquer mudança.**

| Variável | Valor |
|----------|-------|
| `DATABASE_URL` | Neon **pooler** (`...-pooler... ?channel_binding=require&sslmode=require`) |
| `DATABASE_URL_UNPOOLED` | Neon **direta** (DDL/migrações) |
| `SECRET_KEY` | `python -c "import secrets; print(secrets.token_urlsafe(64))"` |
| `ALGORITHM` | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` |
| `MERCADOPAGO_ACCESS_TOKEN` | `APP_USR-...` (produção) |
| `MERCADOPAGO_PUBLIC_KEY` | `APP_USR-...` (mesma aplicação) |
| `MERCADOPAGO_WEBHOOK_SECRET` | hex do painel MP |
| `WEBHOOK_URL` | `https://jpcroco.vercel.app/api/webhook/mercadopago` |
| `FRONTEND_URL` | `https://jpcroco.vercel.app` |
| `CORS_ORIGINS` | `https://jpcroco.vercel.app` |
| `SUPERFRETE_TOKEN/API_URL/EMAIL/SERVICES` | token do painel (`#/integrations`) |
| `MELHORENVIO_TOKEN/CLIENT_ID/CLIENT_SECRET/REDIRECT_URI/API_URL/EMAIL/SERVICES` | idem |
| `MELHORENVIO_FROM_*` | remetente da etiqueta (11 vars) |
| `CEP_ORIGEM` | CEP da loja |
| `BLOB_READ_WRITE_TOKEN` | **store PÚBLICO** do Vercel Blob |
| `VAPID_PUBLIC_KEY/PRIVATE_KEY/SUBJECT` | push do admin |
| `SMTP_HOST/PORT/USER/PASS/FROM` | Gmail: senha de app |
| `WHATSAPP_API_URL/TOKEN` | opcional |

### 3. Banco (Neon)

1. Crie o projeto/branch no Neon (região São Paulo).
2. Aplique o schema: `psql "$DATABASE_URL_UNPOOLED" -f schema.sql` (sem `OWNER`).
3. Crie o admin (ver README §9, trocando a conexão pela do Neon).
4. Fluxo OAuth do Melhor Envio (opcional): cadastre no app do ME a redirect
   `https://jpcroco.vercel.app/api/frete/oauth/callback`, faça deploy e abra
   `GET /api/frete/oauth/url` logado como admin para autorizar.

### 4. Webhooks a cadastrar nos painéis

- Mercado Pago → `https://jpcroco.vercel.app/api/webhook/mercadopago`
- Melhor Envio → `https://jpcroco.vercel.app/api/frete/melhorenvio-webhook`

### 5. Conferir o deploy

- `GET /api/health` → `{"status":"ok"}`
- `/api/produtos/?limit=1` → 200 com `cor` e `tamanhos[].cor`
- F5 em `/#/admin` → 200 (HashRouter, sem dependência de rewrite)

---

## Desenvolvimento local (Docker)

```bash
cp backend/.env.example .env   # ou edite o .env raiz
cp db.env.example db.env
docker compose up -d --build
docker compose exec backend python migrate.py up
```

Frontend `http://localhost:8070` • API `http://localhost:8055/health`.

### Logs / parar

```bash
docker compose logs -f backend   # ou frontend, db
docker compose down              # down -v APAGA o banco local
```

## Migrações

```
backend/migrations/*.sql        # versionadas (002_entrega.sql, idempotente)
python migrate.py up|status|down
```

`down` só desmarca (não dropa tabelas). `schema.sql` (raiz e `backend/`) é o dump
canônico `--schema-only` — após mudar o banco, regenere com `pg_dump` e sincronize os dois.

## Segurança (produção)

- [ ] `SECRET_KEY` aleatória e **girada** (o histórico do git já viu segredos — ver README §15)
- [ ] HTTPS (Vercel já entrega) • firewall/rate-limit pelo dashboard
- [ ] Tokens de frete/blob/MP só no dashboard, nunca em arquivo
- [ ] `node_modules/`, `dist/`, `*.env` (menos `*.example`) fora do git — ver `.gitignore`
