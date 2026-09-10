from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
    )

    DATABASE_URL: str
    # Conexão direta (sem pgbouncer) — usada por migrações/DDL. Opcional.
    DATABASE_URL_UNPOOLED: str = ''
    # Pool lazy (min 0 = sem conexão no startup) e enxuto: seguro para
    # serverless (Vercel), onde conexão eager no cold start pode falhar.
    DB_POOL_MIN_SIZE: int = 0
    DB_POOL_MAX_SIZE: int = 1
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    CLIENT_SECRET: str
    CLIENT_ID: int
    SECRET_KEY: str
    ALGORITHM: str
    MERCADOPAGO_ACCESS_TOKEN: str
    # Sem default de teste: chave errada = Brick quebrado silenciosamente.
    # Preencha MERCADOPAGO_PUBLIC_KEY no .env (credenciais de produção).
    MERCADOPAGO_PUBLIC_KEY: str = ''
    # Web Push (VAPID) — push no aparelho do admin mesmo com o site fechado
    VAPID_PUBLIC_KEY: str = ''
    VAPID_PRIVATE_KEY: str = ''
    VAPID_SUBJECT: str = 'mailto:admin@jpcroco.com.br'
    MERCADOPAGO_WEBHOOK_SECRET: str
    # URL pública única do frontend. O Mercado Pago aceita URLs de retorno
    # apenas em HTTPS; configure-a sem caminho, query string ou múltiplas URLs.
    FRONTEND_URL: str = 'http://localhost:8070'
    CORS_ORIGINS: str = 'http://localhost:8080,http://127.0.0.1:8080, http://localhost:5500'
    WEBHOOK_URL: str = ''

    # Melhor Envio (produção) — cálculo/etiquetas sem contrato próprio
    MELHORENVIO_TOKEN: str = ''
    MELHORENVIO_CLIENT_ID: str = ''
    MELHORENVIO_CLIENT_SECRET: str = ''
    MELHORENVIO_REDIRECT_URI: str = 'https://jpcroco.vercel.app/api/frete/oauth/callback'
    MELHORENVIO_API_URL: str = 'https://www.melhorenvio.com.br/api/v2'
    MELHORENVIO_EMAIL: str = ''
    # Filtrar serviços por id (ex: '1,2'). Vazio = todos.
    MELHORENVIO_SERVICES: str = ''
    # Remetente da etiqueta (fase 2)
    MELHORENVIO_FROM_NOME: str = ''
    MELHORENVIO_FROM_DOCUMENTO: str = ''
    MELHORENVIO_FROM_ENDERECO: str = ''
    MELHORENVIO_FROM_NUMERO: str = ''
    MELHORENVIO_FROM_COMPLEMENTO: str = ''
    MELHORENVIO_FROM_BAIRRO: str = ''
    MELHORENVIO_FROM_CIDADE: str = ''
    MELHORENVIO_FROM_UF: str = ''
    MELHORENVIO_FROM_CEP: str = ''
    MELHORENVIO_FROM_TELEFONE: str = ''
    MELHORENVIO_FROM_EMAIL: str = ''
    # Correios CWS
    CORREIOS_USER: str = ''
    CORREIOS_SENHA: str = ''
    # Cartão de postagem (obrigatório p/ Preço/Prazo) + contrato/DR opcionais.
    CORREIOS_CARTAO: str = ''
    CORREIOS_CONTRATO: str = ''
    CORREIOS_DR: str = ''
    CORREIOS_CEP_ORIGEM: str = '70002900'
    CORREIOS_TOKEN_URL: str = 'https://apihom.correios.com.br/token/v1/autentica'
    CORREIOS_PRECO_URL: str = 'https://apihom.correios.com.br/preco/v1/nacional'
    CORREIOS_PRAZO_URL: str = 'https://apihom.correios.com.br/prazo/v1/nacional'
    CORREIOS_CO_PRODUTO_PAC: str = '04510'
    CORREIOS_CO_PRODUTO_SEDEX: str = '04014'

    WHATSAPP_API_URL: str = ''
    WHATSAPP_TOKEN: str = ''
    VENDEDOR_WHATSAPP: str = '5561999999999'

    SMTP_HOST: str = 'smtp.gmail.com'
    SMTP_PORT: int = 587
    SMTP_USER: str = ''
    SMTP_PASS: str = ''
    SMTP_FROM: str = 'noreply@jpcroco.com.br'

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(',') if o.strip()]


settings = Settings()  # pragma: no cover #type: ignore
