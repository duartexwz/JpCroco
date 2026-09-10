from typing import Optional

from pydantic import BaseModel


class AdminSchema(BaseModel):
    username: str
    password: str
    nome_completo: str


class AdminResponse(BaseModel):
    id: int
    username: str
    nome_completo: str


class AdminUpdate(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None
    nome_completo: Optional[str] = None


class AdminList(BaseModel):
    admins: list[AdminResponse]


class FilterAdmin(BaseModel):
    id: int | None = None
    username: str | None = None
    offset: int | None = 0
    limit: int | None = 10
