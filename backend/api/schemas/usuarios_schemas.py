from typing import Optional

from pydantic import BaseModel


class UsuarioSchema(BaseModel):
    username: str
    password: Optional[str]
    acesso: str
    nome_completo: str


class UsuarioResponse(BaseModel):
    id: int
    username: str
    acesso: str
    nome_completo: str


class UsuarioUpdate(BaseModel):
    username: Optional[str] | None = None
    password: Optional[str] | None = None


class UsuarioList(BaseModel):
    usuarios: list[UsuarioResponse]


class FilterPage(BaseModel):
    offset: int | None = 0
    limit: int | None = 10


class FilterUsuario(BaseModel):
    id: int | None = None
    username: str | None = None
    offset: int | None = 0
    limit: int | None = 10


class Token(BaseModel):
    access_token: str
    token_type: str
