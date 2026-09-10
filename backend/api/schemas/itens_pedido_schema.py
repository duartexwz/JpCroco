from typing import Optional

from pydantic import BaseModel


class ItemSchema(BaseModel):
    pedido_id: int
    produto_id: int
    quantidade: int
    preco_unitario: float
    tamanho: Optional[str] = None


class ItemResponse(BaseModel):
    id: int
    pedido_id: int
    produto_id: int
    quantidade: int
    preco_unitario: float
    tamanho: Optional[str] = None


class ItemUpdate(BaseModel):
    pedido_id: Optional[int] | None = None
    produto_id: Optional[int] | None = None
    quantidade: Optional[int] | None = None
    preco_unitario: Optional[float] | None = None
    tamanho: Optional[str] | None = None


class ItemFilter(BaseModel):
    pedido_id: Optional[int] | None = None
    produto_id: Optional[int] | None = None
    quantidade: Optional[int] | None = None
    preco_unitario: Optional[float] | None = None
    offset: int | None = 0
    limit: int | None = 10


class ItemList(BaseModel):
    itens_pedido: list[ItemResponse]


class FilterPage(BaseModel):
    offset: int | None = 0
    limit: int | None = 10


class Message(BaseModel):
    message: str
