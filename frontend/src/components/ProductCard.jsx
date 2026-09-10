import { api } from '../api/client';

export default function ProductCard({ produto, onDetail }) {
  const semEstoque = (produto.stock ?? 0) <= 0;
  const temPromo = produto.preco_promocional != null && Number(produto.preco_promocional) < Number(produto.preco);
  const tamanhos = produto.tamanhos?.length
    ? produto.tamanhos.map((t) => t.tamanho).join(' / ')
    : produto.tamanho || '';
  const img = produto.imagem || produto.imagens?.[0];

  return (
    <article className="product-card" onClick={() => onDetail(produto)}>
      <div className="product-img">
        {img ? <img src={img} alt={produto.nome} loading="lazy" /> : <span>🐊</span>}
        {semEstoque
          ? <span className="product-tag out">Esgotado</span>
          : (temPromo && <span className="product-tag promo">Promo</span>)}
      </div>
      <div className="product-body">
        <h3 className="product-name">{produto.nome}</h3>
        {tamanhos && <p className="product-size">Tamanhos: {tamanhos}</p>}
        <div className="product-row">
          <span className="product-price">
            {temPromo ? <>{api.formatarMoeda(produto.preco_promocional)}<s>{api.formatarMoeda(produto.preco)}</s></> : api.formatarMoeda(produto.preco)}
          </span>
          <span className={`product-stock${(produto.stock ?? 0) <= 3 && !semEstoque ? ' low' : ''}`}>
            {semEstoque ? 'Sem estoque' : `${produto.stock} em estoque`}
          </span>
        </div>
      </div>
    </article>
  );
}
