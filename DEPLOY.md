# Deploy - JP Croco

Guia completo de deploy do sistema JP Croco (loja-online) em producao.

## Arquitetura

```
[nginx:80] --> Frontend (HTML/CSS/JS estatico)
           --> Proxy reverso para /api/ --> [gunicorn:8000] --> Backend (FastAPI)
                                                              --> PostgreSQL:5432
```

---

## Requisitos

- Docker + Docker Compose v2
- Python 3.13+ (para desenvolvimento local)
- Poetry (para gerenciamento de dependencias)
- Conta MercadoPago com credenciais de producao

---

## 1. Configuracao do Ambiente

### Copiar e preencher .env

```bash
cp backend/.env.example backend/.env
```

### Variaveis obrigatorias para producao

| Variavel | Descricao | Exemplo |
|----------|-----------|---------|
| `SECRET_KEY` | Chave JWT (64+ chars) | `python -c "import secrets; print(secrets.token_urlsafe(64))"` |
| `DATABASE_URL` | URL do PostgreSQL | `postgresql://user:pass@db:5432/loja_online` |
| `MERCADOPAGO_ACCESS_TOKEN` | Token MP producao | `APP_USR-...` |
| `MERCADOPAGO_WEBHOOK_SECRET` | Webhook secret | Hex 64 chars |
| `FRONTEND_URL` | URL do frontend | `https://seudominio.com` |
| `CORS_ORIGINS` | Origens permitidas | `https://seudominio.com` |
| `SMTP_USER` | Email remetente | `seuemail@gmail.com` |
| `SMTP_PASS` | Senha de app Gmail | `xxxx xxxx xxxx xxxx` |

### Gerar SECRET_KEY

```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

---

## 2. Deploy com Docker (Recomendado)

### Build e iniciar

```bash
docker compose up -d --build
```

### Aplicar migracoes do banco

```bash
docker compose exec backend python migrate.py up
```

### Verificar status

```bash
docker compose exec backend python migrate.py status
```

### Criar admin inicial

```bash
docker compose exec backend python -c "
import asyncio
from api.security import get_password_hash
async def create():
    import asyncpg
    conn = await asyncpg.connect('postgresql://loja_admin:adminloja2026@db:5432/loja_online')
    hash_pw = get_password_hash('admin123')
    await conn.execute(
        '''INSERT INTO admins (username, password, acesso, nome_completo)
           VALUES (\$1, \$2, \$3, \$4) ON CONFLICT (username) DO NOTHING''',
        'admin@jpcroco.com', hash_pw, 'admin', 'Administrador'
    )
    await conn.close()
    print('Admin criado com sucesso!')
asyncio.run(create())
"
```

### Semear produtos (opcional)

```bash
docker compose exec backend python seed_produtos.py
```

### URLs de acesso

- Frontend: `http://localhost` (porta 80)
- Backend API: `http://localhost:8000`
- Health check: `http://localhost:8000/health`

### Logs

```bash
docker compose logs -f backend
docker compose logs -f frontend
docker compose logs -f db
```

### Parar

```bash
docker compose down
```

### Parar e apagar dados

```bash
docker compose down -v
```

---

## 3. Deploy Sem Docker

### Backend

```bash
cd backend

# Instalar dependencias
poetry install

# Configurar .env
cp .env.example .env
# Editar .env com suas credenciais

# Aplicar migracoes
poetry run python migrate.py up

# Criar admin
poetry run python -c "..."  # ver secao anterior

# Iniciar producao
poetry run task prod
# ou diretamente:
poetry run gunicorn api.app:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
```

### Frontend

```bash
cd frontend
python -m http.server 8080
```

Ou usar Nginx/Apache para servir os arquivos estaticos.

---

## 4. Migracoes do Banco

### Estrutura

```
backend/migrations/
  001_initial_schema.sql    # Schema inicial (6 tabelas)
backend/migrate.py          # Script de migracao
```

### Comandos

```bash
# Aplicar migracoes pendentes
python migrate.py up

# Verificar status
python migrate.py status

# Marcar ultima migracao como removida (nao dropa tabelas)
python migrate.py down
```

### Criar nova migracao

1. Criar arquivo `backend/migrations/002_nome_da_migracao.sql`
2. Escrever o SQL da migracao
3. Executar `python migrate.py up`

Exemplo:
```sql
-- Migration: 002_adicionar_coluna
-- Data: 2026-09-01
-- Descricao: Adiciona coluna telefone na tabela usuarios

ALTER TABLE usuarios ADD COLUMN telefone VARCHAR(20);
```

---

## 5. Comandos Disponiveis (taskipy)

| Comando | Descricao |
|---------|-----------|
| `poetry run task run` | Servidor dev com hot-reload |
| `poetry run task prod` | Servidor producao (gunicorn) |
| `poetry run task test` | Rodar testes |
| `poetry run task lint` | Verificar codigo (ruff) |
| `poetry run task format` | Formatar codigo |
| `poetry run task migrate` | Aplicar migracoes |
| `poetry run task migrate_status` | Status das migracoes |

---

## 6. Endpoints da API

### Publicos

| Metodo | Endpoint | Descricao |
|--------|----------|-----------|
| POST | `/login` | Login (username + password) |
| POST | `/login/refresh` | Renovar access token |
| POST | `/login/esqueci-senha` | Solicitar redefinicao de senha |
| GET | `/login/redefinir-senha` | Validar token de redefinicao |
| POST | `/login/redefinir-senha` | Redefinir senha com token |
| GET | `/produtos` | Listar produtos |
| GET | `/produtos/{id}` | Detalhes do produto |
| GET | `/health` | Health check |

### Autenticados

| Metodo | Endpoint | Descricao |
|--------|----------|-----------|
| GET | `/pedidos` | Listar pedidos do usuario |
| POST | `/pedidos` | Criar pedido |
| GET | `/cliente` | Dados do cliente |
| POST | `/cliente` | Criar cliente |
| PATCH | `/cliente` | Atualizar cliente |
| POST | `/pagamento/criar-preferencia` | Criar preferencia MercadoPago |

### Admin

| Metodo | Endpoint | Descricao |
|--------|----------|-----------|
| GET | `/usuarios` | Listar usuarios |
| POST | `/usuarios` | Criar usuario |
| PATCH | `/usuarios/{id}` | Atualizar usuario |
| DELETE | `/usuarios/{id}` | Deletar usuario |
| GET | `/pedidos` | Listar todos os pedidos |
| PATCH | `/pedidos/{id}` | Atualizar pedido |
| DELETE | `/pedidos/{id}` | Deletar pedido |
| GET | `/produtos` | Listar todos (incl. inativos) |
| POST | `/produtos` | Criar produto |
| PATCH | `/produtos/{id}` | Atualizar produto |
| DELETE | `/produtos/{id}` | Deletar produto |

---

## 7. Pagamento (MercadoPago)

### Fluxo

1. Frontend cria preferencia via `POST /pagamento/criar-preferencia`
2. Backend retorna `init_point` (URL de pagamento)
3. Usuario e redirecionado para o MercadoPago
4. Apos pagamento, MercadoPago redireciona para `FRONTEND_URL/?pagamento=sucesso|falha`
5. Frontend exibe toast de confirmacao

### Configuracao

- `MERCADOPAGO_ACCESS_TOKEN`: Token de producao (nao sandbox)
- `FRONTEND_URL`: Precisa comecar com `https://` para `auto_return` funcionar
- Webhooks: Configurar no painel MercadoPago apontando para `https://seudominio/api/pagamento/webhook`

---

## 8. Seguranca

### O que foi implementado

- JWT com SECRET_KEY de 64+ caracteres
- CORS configuravel por variavel de ambiente
- Metodos HTTP restritos (GET, POST, PATCH, DELETE)
- Senhas com hash Argon2
- Tokens de reset com expiracao (30 min)
- Migracao do banco de dados via SQL versionado
- Print de tokens removido (usa logging)

### Para producao

- [ ] Trocar `SECRET_KEY` por valor gerado aleatoriamente
- [ ] Usar HTTPS (Nginx reverse proxy com Let's Encrypt)
- [ ] Configurar rate limiting no Nginx
- [ ] Configurar firewall (apenas portas 80/443)
- [ ] Monitorar logs com algum servico (Sentry, etc.)

---

## 9. Variaveis de Ambiente (.env)

```
backend/.env             # Configuracoes locais (nao commitar)
backend/.env.example     # Template para novos ambientes
backend/.env.test        # Configuracoes para testes
```

Nunca commite o arquivo `.env`. O `.gitignore` ja esta configurado para isso.

---

## 10. Troubleshooting

### Erro de conexao com banco

```bash
# Verificar se PostgreSQL esta rodando
docker compose ps db

# Testar conexao
docker compose exec db psql -U loja_admin -d loja_online -c "SELECT 1"
```

### Erro CORS

Verificar se `CORS_ORIGINS` no `.env` inclui a origem do frontend.

### MercadoPago nao redireciona

`auto_return` so funciona com `FRONTEND_URL` iniciando por `https://`.

### Email nao envia

Verificar credenciais SMTP. Para Gmail, usar senha de app (nao senha da conta).
