import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import { useAuth } from '../store/AuthContext';
import { useToast } from '../store/ToastContext';
import TrackingBox, { badgeClass, whatsappPedido } from '../components/Tracking';

export default function MinhasCompras() {
  const { user } = useAuth();
  const { toast } = useToast();
  const navigate = useNavigate();
  const [pedidos, setPedidos] = useState([]);
  const [produtos, setProdutos] = useState(new Map());
  const [itensMap, setItensMap] = useState(new Map());
  const [filtro, setFiltro] = useState('todos');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!user) { navigate('/login', { replace: true }); return; }
    (async () => {
      try {
        const [data, prods] = await Promise.all([
          api.getMeusPedidos(),
          api.getProdutos({ limit: 1000 }).catch(() => ({ produtos: [] })),
        ]);
        const map = new Map();
        (prods.produtos || []).forEach((p) => map.set(p.id, p));
        setProdutos(map);
        const lista = (data.pedidos || []).slice().sort((a, b) => b.id - a.id);
        setPedidos(lista);
        const itensAll = await Promise.all(
          lista.map((p) => api.getItensPedido({ pedido_id: p.id, limit: 1000 })
            .then((r) => ({ pid: p.id, itens: r.itens_pedido || r.itens || [] }))
            .catch(() => ({ pid: p.id, itens: [] }))),
        );
        setItensMap(new Map(itensAll.map((x) => [x.pid, x.itens])));
      } catch (e) {
        toast(e.message, 'error');
      } finally {
        setLoading(false);
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user]);

  const nomeCliente = async () => {
    try {
      if (user?.username?.includes('@')) {
        const c = await api.getClienteByEmail(user.username).catch(() => null);
        if (c?.nome) return c.nome;
      }
    } catch { /* ignore */ }
    return user?.username || 'cliente';
  };

  const lista = filtro === 'todos' ? pedidos : pedidos.filter((p) => String(p.status || '').toLowerCase() === filtro.toLowerCase());

  return (
    <main>
      <div className="page-hero"><div className="container">
        <h1>🛍️ Minhas Compras</h1>
        <p>Acompanhe seus pedidos, entrega e rastreio em tempo real — entrega para todo o Brasil via Correios.</p>
      </div></div>
      <div className="container" style={{ paddingBottom: 48 }}>
        <div className="chips">
          {[['todos', 'Todos'], ['Pago', 'Pagos'], ['Enviado', 'Enviados'], ['Entregue', 'Entregues'], ['pendente', 'Pendentes']].map(([v, l]) => (
            <button key={v} className={`chip${filtro === v ? ' active' : ''}`} onClick={() => setFiltro(v)}>{l}</button>
          ))}
        </div>
        {loading ? <div className="spinner" /> : pedidos.length === 0 ? (
          <div className="empty">
            <div className="empty-icon">🛍️</div>
            <h3>Você ainda não tem pedidos</h3>
            <p>Que tal explorar nossa coleção?</p>
            <Link to="/loja" className="btn btn-primary" style={{ marginTop: 12 }}>Ver produtos</Link>
          </div>
        ) : lista.length === 0 ? (
          <div className="empty"><p>Nenhum pedido com este status.</p></div>
        ) : lista.map((p) => {
          const itens = itensMap.get(p.id) || [];
          const isLocal = p.entrega_tipo?.includes('Retirada') || p.entrega_tipo?.includes('Uber');
          return (
            <div className="order-card" key={p.id}>
              <div className="order-top">
                <div>
                  <b>{p.id_pedido ? `Pedido ${p.id_pedido}` : 'Pedido em processamento'}</b>
                  <div style={{ fontSize: '.8rem', color: 'var(--cinza-500)' }}>{p.entrega_tipo || 'Entrega'} • {api.formatarMoeda(p.valor_total)}</div>
                </div>
                <span className={`badge ${badgeClass(p.status)}`}>{p.status}</span>
              </div>
              <div className="order-body">
                <div>
                  <b style={{ fontSize: '.9rem' }}>Itens ({itens.length})</b>
                  <div style={{ marginTop: 8 }}>
                    {itens.length ? itens.map((i, idx) => {
                      const prod = produtos.get(i.produto_id);
                      return (
                        <div className="item-row" key={idx}>
                          <div className="item-thumb">{prod?.imagem ? <img src={prod.imagem} alt="" /> : '🐊'}</div>
                          <div>
                            <div style={{ fontWeight: 700, fontSize: '.88rem' }}>{prod?.nome || 'Produto'}</div>
                            <div style={{ fontSize: '.78rem', color: 'var(--cinza-500)' }}>{i.quantidade}x • {i.tamanho ? `Tam: ${i.tamanho} • ` : ''}{api.formatarMoeda(i.preco_unitario)}</div>
                          </div>
                        </div>
                      );
                    }) : <div className="item-row">Itens em processamento...</div>}
                  </div>
                </div>
                <div>
                  <div style={{ background: 'var(--fundo)', border: '1px solid var(--cinza-100)', borderRadius: 10, padding: 12 }}>
                    <div className="summary-row"><span>Subtotal</span><span>{api.formatarMoeda(p.subtotal ?? p.valor_total)}</span></div>
                    {(p.valor_frete ?? 0) > 0 && <div className="summary-row"><span>Frete</span><span>{api.formatarMoeda(p.valor_frete)}</span></div>}
                    <div className="summary-row total"><span>Total pago</span><span>{api.formatarMoeda(p.valor_total)}</span></div>
                    <div style={{ fontSize: '.82rem', color: 'var(--cinza-500)', marginTop: 8, background: '#fff', border: '1px dashed var(--cinza-200)', borderRadius: 8, padding: 8 }}>
                      <b>{isLocal ? p.entrega_tipo : 'Entrega'}:</b><br />{p.endereco_entrega}
                      {p.cep_destino && <><br />CEP: {p.cep_destino}</>}
                    </div>
                  </div>
                  <TrackingBox pedido={p} />
                  {isLocal && (
                    <div style={{ marginTop: 10, padding: 12, background: 'var(--ok-bg)', border: '1px solid #c8e6c9', borderRadius: 10 }}>
                      <b style={{ fontSize: '.88rem' }}>{p.entrega_tipo.includes('Retirada') ? '🏪 Retirada na loja' : '🚗 Entrega via Uber'}</b><br />
                      <button className="btn btn-wpp btn-sm btn-block" style={{ marginTop: 8 }}
                        onClick={async () => whatsappPedido(p, await nomeCliente())}>
                        {p.entrega_tipo.includes('Retirada') ? 'Solicitar endereço da loja' : 'Chamar vendedor no WhatsApp'}
                      </button>
                    </div>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </main>
  );
}
