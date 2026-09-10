import { useEffect, useMemo, useState } from 'react';
import { api } from '../api/client';
import ProductCard from '../components/ProductCard';
import ProductModal from '../components/ProductModal';

export default function Loja({ onOpenCart }) {
  const [produtos, setProdutos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [erro, setErro] = useState('');
  const [filtro, setFiltro] = useState('todos');
  const [busca, setBusca] = useState('');
  const [detalhe, setDetalhe] = useState(null);

  const carregar = async () => {
    setLoading(true);
    setErro('');
    try {
      const data = await api.getProdutos({ limit: 100 });
      setProdutos(data.produtos || []);
    } catch (e) {
      setErro(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { carregar(); }, []);

  const tamanhos = useMemo(() => {
    const s = new Set();
    produtos.forEach((p) => {
      if (p.tamanhos?.length) p.tamanhos.forEach((t) => s.add(t.tamanho));
      else if (p.tamanho) s.add(p.tamanho);
    });
    return [...s];
  }, [produtos]);

  const filtrados = produtos.filter((p) => {
    const okTam = filtro === 'todos'
      || (p.tamanhos?.length ? p.tamanhos.some((t) => t.tamanho === filtro) : p.tamanho === filtro);
    const okBusca = !busca.trim() || p.nome.toLowerCase().includes(busca.toLowerCase().trim());
    return okTam && okBusca;
  });

  return (
    <main>
      <div className="page-hero">
        <div className="container">
          <span className="eyebrow">Coleção Completa</span>
          <h1>A Loja 🐊</h1>
          <p>Explore todos os nossos produtos e encontre peças que definem o seu estilo.</p>
        </div>
      </div>
      <div className="container" style={{ paddingBottom: 48 }}>
        <div className="filters-bar">
          <div className="filters-btns">
            <button className={`filter-btn${filtro === 'todos' ? ' active' : ''}`} onClick={() => setFiltro('todos')}>Todos</button>
            {tamanhos.map((t) => (
              <button key={t} className={`filter-btn${filtro === t ? ' active' : ''}`} onClick={() => setFiltro(t)}>{t}</button>
            ))}
          </div>
          <div className="search-box">🔎<input value={busca} onChange={(e) => setBusca(e.target.value)} placeholder="Buscar produto..." /></div>
        </div>
        <p className="count-text"><b>{filtrados.length}</b> produto{filtrados.length !== 1 ? 's' : ''} encontrado{filtrados.length !== 1 ? 's' : ''}</p>
        {loading ? (
          <div className="grid-products">{[0, 1, 2, 3, 4, 5, 6, 7].map((i) => <div key={i} className="skeleton-card" />)}</div>
        ) : erro ? (
          <div className="empty">
            <div className="empty-icon">😕</div>
            <p>Não foi possível carregar os produtos: {erro}</p>
            <button className="btn btn-outline btn-sm" onClick={carregar} style={{ marginTop: 12 }}>Tentar Novamente</button>
          </div>
        ) : filtrados.length === 0 ? (
          <div className="empty">
            <div className="empty-icon">🔎</div>
            <h3>Nenhum produto encontrado</h3>
            <p>Tente buscar por outro termo ou ajustar os filtros.</p>
          </div>
        ) : (
          <div className="grid-products">
            {filtrados.map((p) => <ProductCard key={p.id} produto={p} onDetail={setDetalhe} />)}
          </div>
        )}
      </div>
      {detalhe && <ProductModal produto={detalhe} onClose={(added) => { setDetalhe(null); if (added) onOpenCart(); }} />}
    </main>
  );
}
