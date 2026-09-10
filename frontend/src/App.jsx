import { Suspense, lazy, useState } from 'react';
import { HashRouter, Link, Navigate, Route, Routes, useLocation } from 'react-router-dom';
import Header from './components/Header';
import Footer from './components/Footer';
import CartDrawer from './components/CartDrawer';
import CheckoutModal from './components/CheckoutModal';
import PaymentModal from './components/PaymentModal';
import { api } from './api/client';
import { AuthProvider, useAuth } from './store/AuthContext';
import { CartProvider } from './store/CartContext';
import { ToastProvider, useToast } from './store/ToastContext';
import Home from './pages/Home';
// Rotas fora da home carregam sob demanda (code-split: primeiro paint menor).
const Loja = lazy(() => import('./pages/Loja'));
const Login = lazy(() => import('./pages/Login'));
const Conta = lazy(() => import('./pages/Conta'));
const MinhasCompras = lazy(() => import('./pages/MinhasCompras'));
const Admin = lazy(() => import('./pages/Admin'));
const RedefinirSenha = lazy(() => import('./pages/RedefinirSenha'));
const Politica = lazy(() => import('./pages/Politica'));

function RequerAuth({ children }) {
  const { user, ready } = useAuth();
  const loc = useLocation();
  if (!ready) return <div className="spinner" />;
  if (!user) return <Navigate to="/login" replace state={{ from: loc.pathname }} />;
  return children;
}

function RequerAdmin({ children }) {
  const { user, ready } = useAuth();
  if (!ready) return <div className="spinner" />;
  if (!user) return <Navigate to="/login" replace />;
  if (user.acesso !== 'admin') return <Navigate to="/" replace />;
  return children;
}

function Shell() {
  const [cartOpen, setCartOpen] = useState(false);
  const [checkoutOpen, setCheckoutOpen] = useState(false);
  const [payOrder, setPayOrder] = useState(null);
  const [success, setSuccess] = useState(null);
  const { toast } = useToast();
  const { isLogged } = useAuth();

  const iniciarCheckout = () => {
    if (!isLogged) {
      toast('Faça login para comprar.', 'error');
      window.location.href = '/#/login';
      return;
    }
    setCartOpen(false);
    setCheckoutOpen(true);
  };

  const aposPagar = async (order) => {
    setPayOrder(null);
    // O backend oculta o protocolo enquanto o pedido está pendente; após a
    // aprovação, busca o protocolo real (nunca o #id interno) p/ exibir.
    let protocolo = order.protocolo || null;
    try {
      const data = await api.getMeusPedidos();
      const achado = (data.pedidos || []).find((p) => p.id === order.idPedido);
      if (achado?.id_pedido) protocolo = achado.id_pedido;
    } catch { /* mantém texto neutro */ }
    setSuccess({ ...order, protocolo });
  };

  return (
    <>
      <Header onOpenCart={() => setCartOpen(true)} />
      <Suspense fallback={<div className="spinner" style={{ margin: '60px auto' }} />}>
      <Routes>
        <Route path="/" element={<Home onOpenCart={() => setCartOpen(true)} />} />
        <Route path="/loja" element={<Loja onOpenCart={() => setCartOpen(true)} />} />
        <Route path="/login" element={<Login />} />
        <Route path="/redefinir-senha" element={<RedefinirSenha />} />
        <Route path="/politica-privacidade" element={<Politica />} />
        <Route path="/conta" element={<RequerAuth><Conta /></RequerAuth>} />
        <Route path="/minhas-compras" element={<RequerAuth><MinhasCompras /></RequerAuth>} />
        <Route path="/admin" element={<RequerAdmin><Admin /></RequerAdmin>} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
      </Suspense>
      <Footer />

      <CartDrawer open={cartOpen} onClose={() => setCartOpen(false)} onCheckout={iniciarCheckout} />
      <CheckoutModal open={checkoutOpen} onClose={() => setCheckoutOpen(false)} onPaid={(o) => setPayOrder(o)} />
      <PaymentModal order={payOrder} onClose={() => setPayOrder(null)} onSuccess={aposPagar} />

      {success && (
        <div className="modal-overlay show" onClick={() => setSuccess(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-body">
              <div className="modal-icon">✅</div>
              <h2 className="modal-title">Pagamento aprovado!</h2>
              <p className="modal-text">
                {success.protocolo ? <>Pedido <b>{success.protocolo}</b></> : 'Pedido recebido'} confirmado com sucesso.<br />
                Total: <b>{success.valorTotal?.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}</b>
                {success.entrega_tipo ? <><br />Entrega: {success.entrega_tipo}</> : null}
              </p>
              <div style={{ display: 'flex', gap: 8, flexDirection: 'column' }}>
                <Link to="/minhas-compras" className="btn btn-primary btn-block">Acompanhar em Minhas Compras</Link>
                <button className="btn btn-ghost btn-block" onClick={() => setSuccess(null)}>Continuar Comprando</button>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

export default function App() {
  return (
    <HashRouter>
      <AuthProvider>
        <CartProvider>
          <ToastProvider>
            <Shell />
          </ToastProvider>
        </CartProvider>
      </AuthProvider>
    </HashRouter>
  );
}
