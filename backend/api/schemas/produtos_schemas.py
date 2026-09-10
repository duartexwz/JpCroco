from typing import Optional

from pydantic import BaseModel, ConfigDict


class TamanhoSchema(BaseModel):
    tamanho: str
    stock: int = 0
    preco: Optional[float] = None


class ProdutosSchema(BaseModel):
    nome: str
    preco: float
    imagem: Optional[str] = None
    imagens: Optional[list[str]] = None
    preco_promocional: Optional[float] = None
    tamanhos: list[TamanhoSchema] = []


class ProdutosResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    preco: float
    tamanho: Optional[str] = None
    stock: int = 0
    imagem: Optional[str] = None
    imagens: list[str] = []
    preco_promocional: Optional[float] = None
    tamanhos: list[TamanhoSchema] = []


class ProdutosUpdate(BaseModel):
    nome: Optional[str] = None
    preco: Optional[float] = None
    imagem: Optional[str] = None
    imagens: Optional[list[str]] = None
    preco_promocional: Optional[float] = None
    tamanhos: Optional[list[TamanhoSchema]] = None


class ProdutosList(BaseModel):
    produtos: list[ProdutosResponse]


class Token(BaseModel):
    access_token: str
    token_type: str


class FilterPage(BaseModel):
    offset: int | None = 0
    limit: int | None = 10


class FilterProdutos(BaseModel):
    nome: str | None = None
    preco_min: float | None = None
    preco_max: float | None = None
    tamanho: str | None = None
    stock_min: int | None = None
    stock_max: int | None = None
    offset: int | None = 0
    limit: int | None = 10


class Message(BaseModel):
    message: str
