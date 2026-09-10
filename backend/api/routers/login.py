from http import HTTPStatus
from typing import Annotated
import logging

import asyncpg
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from pydantic import BaseModel

from api.database import get_db
from api.schemas.produtos_schemas import Token
from api.security import create_access_token, create_reset_token, get_current_user, get_password_hash, verify_password, verify_reset_token
from api.settings import settings

router = APIRouter(
    prefix='/login',
    tags=['login'],
)

logger = logging.getLogger(__name__)


database_loja = Annotated[asyncpg.Connection, Depends(get_db)]
oauth2_scheme = Annotated[OAuth2PasswordRequestForm, Depends()]
CurrentUser = Annotated[dict, Depends(get_current_user)]


mail_config = ConnectionConfig(
    MAIL_USERNAME=settings.SMTP_USER,
    MAIL_PASSWORD=settings.SMTP_PASS,
    MAIL_FROM=settings.SMTP_FROM,
    MAIL_PORT=settings.SMTP_PORT,
    MAIL_SERVER=settings.SMTP_HOST,
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
)

fm = FastMail(mail_config)


@router.post('/', status_code=HTTPStatus.OK)
async def login(db: database_loja, form_data: oauth2_scheme):
    query_admin = """
    SELECT id, username, password, acesso
    FROM admins
    WHERE username = $1
    """

    user_record = await db.fetchrow(query_admin, form_data.username)

    if not user_record:
        query_usuario = """
        SELECT id, username, password, acesso
        FROM usuarios
        WHERE username = $1
        """

        user_record = await db.fetchrow(query_usuario, form_data.username)

    if not user_record:
        raise HTTPException(
            status_code=HTTPStatus.UNAUTHORIZED,
            detail='Senha invalida ou email invalido.',
        )

    user = dict(user_record)

    if not verify_password(form_data.password, user['password']):
        raise HTTPException(
            status_code=HTTPStatus.UNAUTHORIZED,
            detail='Senha invalida ou email invalido.',
        )

    access_token = await create_access_token(data={'sub': user['username'], 'acesso': user['acesso']})
    return {'access_token': access_token, 'token_type': 'bearer'}


@router.post('/refresh_login', response_model=Token)
async def refreash_access_token(current_user: CurrentUser):

    identifier = getattr(current_user, 'username', None) or getattr(current_user, 'nome', None)
    new_access_token = await create_access_token(data={'sub': identifier})

    return {'access_token': new_access_token, 'token_type': 'bearer'}


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    nova_senha: str


async def _enviar_email(destinatario: str, link: str):
    if not settings.SMTP_USER:
        logger.warning('SMTP nao configurado. Link de redefinicao: %s', link)
        return

    html = f"""<!DOCTYPE html>
<html lang="pt-br">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin:0;padding:0;background-color:#f4f4f0;font-family:'Helvetica Neue',Helvetica,Arial,sans-serif">
  <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#f4f4f0;padding:40px 0">
    <tr>
      <td align="center">
        <table width="560" cellpadding="0" cellspacing="0" style="background-color:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,0.08)">

          <!-- HEADER -->
          <tr>
            <td style="background-color:#1a472a;padding:32px 40px;text-align:center">
              <h1 style="color:#ffffff;font-size:28px;font-weight:700;letter-spacing:3px;margin:0">JP CROCO</h1>
            </td>
          </tr>

          <!-- BODY -->
          <tr>
            <td style="padding:48px 40px 40px">
              <h2 style="color:#1a472a;font-size:22px;font-weight:700;margin:0 0 16px;text-align:center">Redefinir sua senha</h2>
              <p style="color:#4a4a42;font-size:15px;line-height:1.6;margin:0 0 24px;text-align:center">
                Voce solicitou a redefinicao da sua senha. Clique no botao abaixo para criar uma nova senha segura:
              </p>

              <!-- BOTAO -->
              <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td align="center" style="padding:0 0 32px">
                    <a href="{link}" style="display:inline-block;background-color:#1a472a;color:#ffffff;font-size:16px;font-weight:600;text-decoration:none;padding:16px 48px;border-radius:8px;letter-spacing:0.5px">
                      Redefinir Minha Senha
                    </a>
                  </td>
                </tr>
              </table>

              <!-- SEPARADOR -->
              <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td style="border-top:1px solid #e8e8e4;padding:0"></td>
                </tr>
              </table>

              <!-- INFO -->
              <table width="100%" cellpadding="0" cellspacing="0" style="margin-top:24px">
                <tr>
                  <td style="padding:8px 0">
                    <p style="color:#9e9e96;font-size:13px;line-height:1.5;margin:0">
                      <strong style="color:#6e6e66">Este link expira em 30 minutos.</strong>
                    </p>
                  </td>
                </tr>
                <tr>
                  <td style="padding:8px 0">
                    <p style="color:#9e9e96;font-size:13px;line-height:1.5;margin:0">
                      Se voce nao solicitou esta alteracao, ignore este email. Sua senha atual continua segura.
                    </p>
                  </td>
                </tr>
                <tr>
                  <td style="padding:8px 0">
                    <p style="color:#9e9e96;font-size:13px;line-height:1.5;margin:0">
                      <strong style="color:#6e6e66">Link direto:</strong><br>
                      <a href="{link}" style="color:#1a472a;font-size:12px;word-break:break-all">{link}</a>
                    </p>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- FOOTER -->
          <tr>
            <td style="background-color:#f9f9f6;padding:24px 40px;text-align:center;border-top:1px solid #e8e8e4">
              <p style="color:#9e9e96;font-size:12px;margin:0">
                JP Croco &copy; 2026 - Todos os direitos reservados
              </p>
              <p style="color:#c0c0b8;font-size:11px;margin:8px 0 0">
                Estilo, elegancia e qualidade desde 2026
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""

    texto_plano = f"""JP CROCO - Redefinir sua senha

Voce solicitou a redefinicao da sua senha.

Acesse o link abaixo para criar uma nova senha:
{link}

Este link expira em 30 minutos.

Se voce nao solicitou esta alteracao, ignore este email. Sua senha atual continua segura.

---
JP Croco - 2026
"""

    message = MessageSchema(
        subject='JP Croco - Redefinir sua senha',
        recipients=[destinatario],
        body=texto_plano,
        html=html,
        subtype='html',
    )

    try:
        await fm.send_message(message)
    except Exception as e:
        logger.error('Erro ao enviar email para %s: %s', destinatario, e)


@router.post('/esqueci-senha', status_code=HTTPStatus.OK)
async def esqueci_senha(dados: ForgotPasswordRequest, db: database_loja):
    query = "SELECT id, username FROM usuarios WHERE username = $1"
    user = await db.fetchrow(query, dados.email)

    if not user:
        query_admin = "SELECT id, username FROM admins WHERE username = $1"
        user = await db.fetchrow(query_admin, dados.email)

    username = None
    email_destino = dados.email

    if user:
        username = user['username']
    else:
        query_cliente = "SELECT email FROM clientes WHERE email = $1"
        cliente = await db.fetchrow(query_cliente, dados.email)
        if cliente:
            email_destino = cliente['email']

    token_sub = username or dados.email
    reset_token = await create_reset_token(token_sub)
    frontend_url = settings.FRONTEND_URL
    link = f'{frontend_url}/redefinir-senha?token={reset_token}'

    await _enviar_email(email_destino, link)

    return {'message': 'Se o email estiver cadastrado, voce recebera um link para redefinir a senha.'}


@router.post('/redefinir-senha', status_code=HTTPStatus.OK)
async def redefinir_senha(dados: ResetPasswordRequest, db: database_loja):
    email = await verify_reset_token(dados.token)

    if not email:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail='Link invalido ou expirado. Solicite um novo link.',
        )

    if len(dados.nova_senha) < 6:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail='A senha deve ter no minimo 6 caracteres.',
        )

    hashed = get_password_hash(dados.nova_senha)

    query = "UPDATE usuarios SET password = $1 WHERE username = $2 RETURNING id"
    result = await db.fetchrow(query, hashed, email)

    if not result:
        query_admin = "UPDATE admins SET password = $1 WHERE username = $2 RETURNING id"
        result = await db.fetchrow(query_admin, hashed, email)

    if not result:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Usuario nao encontrado.',
        )

    return {'message': 'Senha redefinida com sucesso! Voce pode fazer login agora.'}
