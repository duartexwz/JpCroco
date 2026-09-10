from typing import Optional

from pydantic import BaseModel, EmailStr


class ClientesSchema(BaseModel):
    nome: str
    email: EmailStr
    telefone: str
    cpf: str


class ClientesResponse(BaseModel):
    id: int
    nome: str
    email: EmailStr
    telefone: str
    cpf: str


class ClientesUpdate(BaseModel):
    nome: Optional[str] | None = None
    email: Optional[EmailStr] | None = None
    telefone: Optional[str] | None = None
    cpf: Optional[str] | None = None


class ClientesFilter(BaseModel):
    nome: Optional[str] | None = None
    email: Optional[str] | None = None
    telefone: Optional[str] | None = None
    cpf: Optional[str] | None = None
    offset: int | None = 0
    limit: int | None = 10


class ClientesList(BaseModel):
    clientes: list[ClientesResponse]


class FilterPage(BaseModel):
    offset: int | None = 0
    limit: int | None = 10


class Token(BaseModel):
    access_token: str
    token_type: str


class Message(BaseModel):
    message: str
