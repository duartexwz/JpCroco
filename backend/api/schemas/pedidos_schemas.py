from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel


class PedidosSchema(BaseModel):
    cliente_id: int
    status: str
    endereco_entrega: str
    valor_total: Decimal
    entrega_tipo: Optional[str] = 'Correios'
    valor_frete: Optional[Decimal] = Decimal('0.00')
    subtotal: Optional[Decimal] = None
    cep_destino: Optional[str] = None


class PedidosResponseSchema(BaseModel):
    id: int
    cliente_id: int
    status: str
    endereco_entrega: str
    id_pedido: Optional[str] = None
    valor_total: Decimal
    codigo_rastreio: Optional[str] = None
    data_envio: Optional[datetime] = None
    transportadora: Optional[str] = None
    entrega_tipo: Optional[str] = None
    valor_frete: Optional[Decimal] = None
    subtotal: Optional[Decimal] = None
    cep_destino: Optional[str] = None


class FilterPage(BaseModel):
    offset: int | None = 0
    limit: int | None = 10


class PedidosUpdate(BaseModel):
    cliente_id: Optional[int] = None
    status: Optional[str] = None
    endereco_entrega: Optional[str] = None
    id_pedido: Optional[str] = None
    valor_total: Optional[Decimal] = None
    codigo_rastreio: Optional[str] = None
    transportadora: Optional[str] = None
    entrega_tipo: Optional[str] = None
    valor_frete: Optional[Decimal] = None
    subtotal: Optional[Decimal] = None
    cep_destino: Optional[str] = None


class PedidosList(BaseModel):
    pedidos: list[PedidosResponseSchema]


class Token(BaseModel):
    access_token: str
    token_type: str


class FilterPedidos(BaseModel):
    cliente_id: int | None = None
    data_pedido: datetime | None = None
    status: str | None = None
    endereco_entrega: str | None = None
    id_pedido: str | None = None
    valor_total: Decimal | None = None
    offset: int | None = 0
    limit: int | None = 10


class Message(BaseModel):
    message: str
