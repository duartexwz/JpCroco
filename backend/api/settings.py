from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
    )

    DATABASE_URL: str
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

    # Correios CWS
    CORREIOS_USER: str = ''
    CORREIOS_SENHA: str = ''
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
