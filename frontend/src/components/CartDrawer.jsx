import { Link } from 'react-router-dom';
import { useCart } from '../store/CartContext';
import { api } from '../api/client';

export default function CartDrawer({ open, onClose, onCheckout }) {
  const { arr, subtotal, alterarQuantidade, remover } = useCart();

  return (
    <>
      <div className={`overlay${open ? ' show' : ''}`} onClick={onClose} />
      <aside className={`drawer${open ? ' open' : ''}`} aria-hidden={!open}>
        <div className="drawer-head">
          <h2>Sacola 🛍️</h2>
          <button className="icon-btn" onClick={onClose}>✕</button>
        </div>
        <div className="drawer-body">
          {arr.length === 0 ? (
            <div className="empty">
              <div className="empty-icon">🛍️</div>
              <h3>Sua sacola está vazia</h3>
              <p>Adicione produtos para começar.</p>
              <Link to="/loja" className="btn btn-primary" onClick={onClose} style={{ marginTop: 14 }}>Ver Produtos</Link>
            </div>
          ) : (
            arr.map((item) => (
              <div className="cart-item" key={item.chave}>
                <div className="cart-thumb">{item.imagem ? <img src={item.imagem} alt={item.nome} /> : '🐊'}</div>
                <div className="cart-info">
                  <div className="cart-name">{item.nome}</div>
                  <div className="cart-meta">{item.tamanho ? `Tam: ${item.tamanho}` : ''}</div>
                  <div className="cart-bottom">
                    <div className="qty">
                      <button onClick={() => alterarQuantidade(item.chave, item.quantidade - 1)}>−</button>
                      <span>{item.quantidade}</span>
                      <button onClick={() => alterarQuantidade(item.chave, item.quantidade + 1)}>+</button>
                    </div>
                    <span className="cart-price">{api.formatarMoeda(item.preco * item.quantidade)}</span>
                  </div>
                  <button className="cart-remove" onClick={() => remover(item.chave)}>Remover</button>
                </div>
              </div>
            ))
          )}
        </div>
        {arr.length > 0 && (
          <div className="drawer-foot">
            <div className="summary-row"><span>Subtotal</span><span>{api.formatarMoeda(subtotal)}</span></div>
            <div className="summary-row total"><span>Total</span><span>{api.formatarMoeda(subtotal)}</span></div>
            <p className="form-hint" style={{ margin: '6px 0 10px' }}>Frete calculado no próximo passo por CEP.</p>
            <button className="btn btn-primary btn-block" onClick={onCheckout}>Finalizar Compra</button>
            <button className="btn btn-ghost btn-block" onClick={onClose}>Continuar Comprando</button>
          </div>
        )}
      </aside>
    </>
  );
}
