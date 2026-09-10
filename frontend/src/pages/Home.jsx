import { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { api } from '../api/client';
import ProductCard from '../components/ProductCard';
import ProductModal from '../components/ProductModal';
import { useToast } from '../store/ToastContext';

export default function Home({ onOpenCart }) {
  const [destaques, setDestaques] = useState([]);
  const [loading, setLoading] = useState(true);
  const [detalhe, setDetalhe] = useState(null);
  const [params, setParams] = useSearchParams();
  const { toast } = useToast();

  useEffect(() => {
    (async () => {
      try {
        const data = await api.getProdutos({ limit: 4 });
        setDestaques(data.produtos || []);
      } catch {
        setDestaques([]);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  // Retorno do Mercado Pago (Checkout Pro) — mesmo comportamento do site antigo
  useEffect(() => {
    const mp = params.get('collection_status') || params.get('status');
    const status = { approved: 'sucesso', rejected: 'falha', cancelled: 'falha', pending: 'pendente', in_process: 'pendente' }[mp] || params.get('pagamento');
    if (!status) return;
    const msgs = {
      sucesso: ['Pagamento aprovado! Seu pedido foi confirmado.', 'success'],
      falha: ['Pagamento não realizado. Tente novamente.', 'error'],
      pendente: ['Pagamento em análise. Você receberá a confirmação em breve.', 'info'],
    };
    const m = msgs[status];
    if (m) setTimeout(() => toast(m[0], m[1]), 400);
    setParams({}, { replace: true });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <>
      <section className="hero">
        <div className="hero-inner">
          <span className="eyebrow">🐊 Coleção Exclusiva 2026</span>
          <h1 className="hero-title">Elegância que nasce da <em>confiança</em></h1>
          <p className="hero-desc">Descubra a nova coleção JP Croco. Peças que unem sofisticação e conforto para quem define o jogo antes de entrá-lo.</p>
          <div className="hero-actions">
            <Link to="/loja" className="btn btn-white">Comprar Agora</Link>
            <a href="#destaques" className="btn btn-outline" style={{ borderColor: 'rgba(255,255,255,.4)', color: '#fff' }}>Ver Destaques</a>
          </div>
          <div className="hero-stats">
            <div><b>🔄 Troca fácil</b><span>em até 30 dias</span></div>
            <div><b>🚚 Brasil todo</b><span>via Correios</span></div>
            <div><b>🔒 100% seguro</b><span>Mercado Pago</span></div>
          </div>
        </div>
      </section>

      <section className="section">
        <div className="container">
          <div className="features">
            <div className="feature">
              <div className="feature-icon">🚚</div>
              <h3>Entrega para todo o Brasil</h3>
              <p>Correios com rastreio em tempo real. No DF: retirada grátis ou Uber a combinar.</p>
            </div>
            <div className="feature">
              <div className="feature-icon">💎</div>
              <h3>Qualidade Premium</h3>
              <p>Materiais selecionados e acabamento impecável em cada peça.</p>
            </div>
            <div className="feature">
              <div className="feature-icon">🔄</div>
              <h3>Troca Fácil</h3>
              <p>Troca gratuita em até 30 dias. Sua satisfação é nossa prioridade.</p>
            </div>
          </div>
        </div>
      </section>

      <section className="section" id="destaques" style={{ paddingTop: 0 }}>
        <div className="container">
          <div className="section-head center">
            <h2 className="section-title">Destaques 🐊</h2>
            <p className="section-sub">As peças mais procuradas da nossa coleção</p>
          </div>
          {loading ? (
            <div className="grid-products">{[0, 1, 2, 3].map((i) => <div key={i} className="skeleton-card" />)}</div>
          ) : destaques.length === 0 ? (
            <p style={{ textAlign: 'center', color: 'var(--cinza-500)' }}>Nenhum produto encontrado.</p>
          ) : (
            <div className="grid-products">
              {destaques.map((p) => <ProductCard key={p.id} produto={p} onDetail={setDetalhe} />)}
            </div>
          )}
          <div style={{ textAlign: 'center', marginTop: 26 }}>
            <Link to="/loja" className="btn btn-primary">Ver Coleção Completa</Link>
          </div>
        </div>
      </section>

      <section className="section" style={{ paddingTop: 0 }}>
        <div className="container">
          <div className="about-grid">
            <div className="about-img">🐊</div>
            <div>
              <span className="eyebrow" style={{ color: 'var(--verde)', background: 'var(--verde-soft)', borderColor: '#cfe6d6' }}>Nossa História</span>
              <h2 className="section-title">Desde 2026, definindo o padrão</h2>
              <p style={{ color: 'var(--cinza-500)', margin: '12px 0 20px' }}>
                A JP Croco nasceu da paixão por moda que ousa. Cada peça é criada pensando em quem não se contenta com o comum.
                Nosso crocodilo é o símbolo de quem lidera com confiança e estilo.
              </p>
              <Link to="/loja" className="btn btn-primary">Ver Coleção</Link>
            </div>
          </div>
        </div>
      </section>

      <section className="section" style={{ paddingTop: 0 }}>
        <div className="container">
          <div className="cta">
            <h2>Pronto para se destacar?</h2>
            <p>Explore nossa coleção completa e encontre a peça que define o seu estilo.</p>
            <Link to="/loja" className="btn btn-white btn-lg">Explorar Loja</Link>
          </div>
        </div>
      </section>

      {detalhe && <ProductModal produto={detalhe} onClose={(added) => { setDetalhe(null); if (added) onOpenCart(); }} />}
    </>
  );
}
