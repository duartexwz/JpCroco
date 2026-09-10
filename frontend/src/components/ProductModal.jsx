import { useState } from 'react';
import { api } from '../api/client';
import { useCart } from '../store/CartContext';
import { useToast } from '../store/ToastContext';

export default function ProductModal({ produto, onClose }) {
  const { adicionar } = useCart();
  const { toast } = useToast();
  const [tamanho, setTamanho] = useState('');
  const [qtd, setQtd] = useState(1);
  const [imgIdx, setImgIdx] = useState(0);

  if (!produto) return null;
  const imagens = produto.imagens?.length ? produto.imagens : (produto.imagem ? [produto.imagem] : []);
  const temPromo = produto.preco_promocional != null && Number(produto.preco_promocional) < Number(produto.preco);
  const semEstoque = (produto.stock ?? 0) <= 0;
  const precisaTamanho = (produto.tamanhos?.length || 0) > 0;

  const comprar = () => {
    if (precisaTamanho && !tamanho) {
      toast('Escolha um tamanho.', 'error');
      return;
    }
    for (let i = 0; i < qtd; i++) adicionar(produto, tamanho);
    toast(`${produto.nome} na sacola!`, 'success');
    onClose(true);
  };

  return (
    <div className="modal-overlay show" onClick={() => onClose(false)}>
      <div className="modal modal-wide" onClick={(e) => e.stopPropagation()} style={{ textAlign: 'left' }}>
        <div className="drawer-head">
          <h2>{produto.nome}</h2>
          <button className="icon-btn" onClick={() => onClose(false)}>✕</button>
        </div>
        <div className="drawer-body">
          <div className="product-img" style={{ borderRadius: 14, aspectRatio: '4/3' }}>
            {imagens[imgIdx] ? <img src={imagens[imgIdx]} alt={produto.nome} /> : <span>🐊</span>}
          </div>
          {imagens.length > 1 && (
            <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
              {imagens.map((u, i) => (
                <img key={i} src={u} alt="" onClick={() => setImgIdx(i)}
                  style={{ width: 56, height: 56, objectFit: 'cover', borderRadius: 8, cursor: 'pointer', border: i === imgIdx ? '2px solid var(--verde)' : '1px solid var(--cinza-200)' }} />
              ))}
            </div>
          )}
          <div style={{ marginTop: 12, display: 'flex', alignItems: 'center', gap: 10 }}>
            <span className="product-price" style={{ fontSize: '1.3rem' }}>
              {temPromo ? <>{api.formatarMoeda(produto.preco_promocional)}<s>{api.formatarMoeda(produto.preco)}</s></> : api.formatarMoeda(produto.preco)}
            </span>
            <span className="product-stock">{semEstoque ? 'Sem estoque' : `${produto.stock} em estoque`}</span>
          </div>
          {precisaTamanho && (
            <div className="form-group" style={{ marginTop: 12 }}>
              <label className="form-label">Tamanho *</label>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                {produto.tamanhos.map((t) => (
                  <button key={t.tamanho} className={`filter-btn${tamanho === t.tamanho ? ' active' : ''}`}
                    disabled={t.stock <= 0} onClick={() => setTamanho(t.tamanho)}>
                    {t.tamanho}{t.stock <= 0 ? ' (esg.)' : ''}
                  </button>
                ))}
              </div>
            </div>
          )}
          <div className="form-group">
            <label className="form-label">Quantidade</label>
            <div className="qty" style={{ width: 'fit-content' }}>
              <button onClick={() => setQtd(Math.max(1, qtd - 1))}>−</button>
              <span>{qtd}</span>
              <button onClick={() => setQtd(Math.min(10, qtd + 1))}>+</button>
            </div>
          </div>
        </div>
        <div className="drawer-foot">
          <button className="btn btn-primary btn-block" onClick={comprar} disabled={semEstoque}>
            {semEstoque ? 'Produto esgotado' : 'Adicionar à Sacola 🛍️'}
          </button>
        </div>
      </div>
    </div>
  );
}
