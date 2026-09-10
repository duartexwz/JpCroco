import { useState } from 'react';
import { Link, NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../store/AuthContext';
import { useCart } from '../store/CartContext';

export default function Header({ onOpenCart }) {
  const { user, isLogged, isAdmin, logout } = useAuth();
  const { totalItens } = useCart();
  const [menu, setMenu] = useState(false);
  const navigate = useNavigate();

  const sair = () => {
    logout();
    setMenu(false);
    navigate('/');
  };

  return (
    <>
      <div className="promo-bar">Entrega para todo o Brasil <b>• Retirada e Uber no DF</b> • Pagamento 100% seguro</div>
      <header className="site-header">
        <div className="container header-inner">
          <Link to="/" className="brand">
            <span className="brand-mark">🐊</span>
            <span className="brand-text">JP CROCO<small>ATITUDE • ESTILO</small></span>
          </Link>
          <nav className="nav-desktop">
            <NavLink to="/" className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}>Início</NavLink>
            <NavLink to="/loja" className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}>Loja</NavLink>
            {isLogged && (
              <>
                {isAdmin && <NavLink to="/admin" className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}>Admin</NavLink>}
                <NavLink to="/minhas-compras" className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}>Minhas Compras</NavLink>
                <NavLink to="/conta" className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}>Minha Conta</NavLink>
                <button className="btn-logout" onClick={sair}>Sair</button>
              </>
            )}
            {!isLogged && <NavLink to="/login" className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}>Entrar</NavLink>}
            <button className="cart-btn" onClick={onOpenCart} aria-label="Abrir sacola">
              🛍️
              {totalItens > 0 && <span className="cart-count">{totalItens}</span>}
            </button>
          </nav>
          <div style={{ display: 'flex', gap: 4, alignItems: 'center' }} className="mobile-only-btns">
            <button className="cart-btn" onClick={onOpenCart} aria-label="Abrir sacola" style={{ width: 40, height: 40 }}>
              🛍️
              {totalItens > 0 && <span className="cart-count">{totalItens}</span>}
            </button>
            <button className="hamburger" onClick={() => setMenu(true)} aria-label="Menu" style={{ display: 'flex' }}>
              <span /><span /><span />
            </button>
          </div>
        </div>
      </header>
      <div className={`mobile-menu${menu ? ' open' : ''}`}>
        <div className="mobile-menu-head">
          <Link to="/" className="brand" onClick={() => setMenu(false)}>
            <span className="brand-mark">🐊</span>
            <span className="brand-text">JP CROCO</span>
          </Link>
          <button className="icon-btn" onClick={() => setMenu(false)}>✕</button>
        </div>
        <nav>
          <Link to="/" className="mobile-link" onClick={() => setMenu(false)}>Início</Link>
          <Link to="/loja" className="mobile-link" onClick={() => setMenu(false)}>Loja</Link>
          {isLogged ? (
            <>
              {isAdmin && <Link to="/admin" className="mobile-link" onClick={() => setMenu(false)}>Admin</Link>}
              <Link to="/minhas-compras" className="mobile-link" onClick={() => setMenu(false)}>Minhas Compras</Link>
              <Link to="/conta" className="mobile-link" onClick={() => setMenu(false)}>Minha Conta {user?.username ? `(${user.username})` : ''}</Link>
              <button className="mobile-link logout" onClick={sair}>Sair</button>
            </>
          ) : (
            <Link to="/login" className="mobile-link" onClick={() => setMenu(false)}>Entrar</Link>
          )}
        </nav>
      </div>
      <style>{`@media(min-width:769px){.mobile-only-btns{display:none!important}}`}</style>
    </>
  );
}
