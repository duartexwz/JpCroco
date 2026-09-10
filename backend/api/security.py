from datetime import datetime, timedelta
from http import HTTPStatus
from typing import Annotated
from zoneinfo import ZoneInfo

from asyncpg import Connection
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jwt import DecodeError, ExpiredSignatureError, InvalidTokenError, decode, encode
from pwdlib import PasswordHash

from api.database import get_db
from api.settings import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl='/login/')
Token = Annotated[str, Depends(oauth2_scheme)]
Database = Annotated[Connection, Depends(get_db)]

password_hash = PasswordHash.recommended()


async def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(tz=ZoneInfo('UTC')) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({'exp': expire})

    encode_jwt = encode(to_encode, settings.SECRET_KEY, algorithm='HS256')

    return encode_jwt


async def create_reset_token(email: str) -> str:
    to_encode = {'sub': email, 'purpose': 'password_reset'}
    expire = datetime.now(tz=ZoneInfo('UTC')) + timedelta(minutes=30)
    to_encode.update({'exp': expire})
    return encode(to_encode, settings.SECRET_KEY, algorithm='HS256')


async def verify_reset_token(token: str) -> str | None:
    try:
        payload = decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get('purpose') != 'password_reset':
            return None
        return payload.get('sub')
    except (DecodeError, ExpiredSignatureError, InvalidTokenError):
        return None


async def get_current_user(token: Token, db: Database) -> dict:

    # breakpoint()
    credentials_exception = HTTPException(
        status_code=HTTPStatus.UNAUTHORIZED,
        detail='Could not validate credentials',
        headers={'WWW-Authenticate': 'Bearer'},
    )

    try:
        payload = decode(token, settings.SECRET_KEY, settings.ALGORITHM)
        subject_email = payload.get('sub')

        if not subject_email:
            raise credentials_exception

    except (DecodeError, ExpiredSignatureError, InvalidTokenError):
        raise credentials_exception

    query_usuarios = 'SELECT id, username, acesso FROM usuarios WHERE username = $1'

    user_record = await db.fetchrow(query_usuarios, subject_email)

    if not user_record:
        query_admins = "SELECT id, username, 'admin' AS acesso FROM admins WHERE username = $1"
        user_record = await db.fetchrow(query_admins, subject_email)

    if not user_record:
        raise credentials_exception

    return dict(user_record)


async def get_current_admin(current_user: dict = Depends(get_current_user)) -> dict:
    if current_user.get('acesso') != 'admin':
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN,
            detail='Você não tem permissão para acessar este recurso.',
        )
    return current_user


def verify_password(plain_password, hashed_password) -> bool:
    try:
        return password_hash.verify(plain_password, hashed_password)
    except Exception:
        return False


def get_password_hash(password) -> str:
    return password_hash.hash(password)
