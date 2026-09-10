import { Link } from 'react-router-dom';

export default function Footer() {
  return (
    <footer className="site-footer">
      <div className="container">
        <div className="footer-grid">
          <div>
            <h4>🐊 JP Croco</h4>
            <span>Estilo, elegância e qualidade desde 2026. Moda que define atitude — do DF para todo o Brasil.</span>
            <span style={{ marginTop: 8 }}>Pagamento seguro via Mercado Pago • Entrega via Correios, Uber ou retirada.</span>
          </div>
          <div>
            <h4>Navegação</h4>
            <Link to="/">Início</Link>
            <Link to="/loja">Loja</Link>
            <Link to="/minhas-compras">Minhas Compras</Link>
            <Link to="/conta">Minha Conta</Link>
          </div>
          <div>
            <h4>Ajuda</h4>
            <Link to="/politica-privacidade">Política de Privacidade</Link>
            <Link to="/loja">Trocas em até 30 dias</Link>
            <a href="https://www2.correios.com.br/sistemas/rastreamento/" target="_blank" rel="noreferrer">Rastrear nos Correios</a>
          </div>
          <div>
            <h4>Atendimento</h4>
            <span>contato@jpcroco.com.br</span>
            <span>(61) 99680-3932</span>
            <span>Seg – Sex: 9h às 18h</span>
          </div>
        </div>
        <div className="footer-bottom">
          <span>© 2026 JP Croco. Todos os direitos reservados.</span>
          <span>Feito com atitude 🐊</span>
        </div>
      </div>
    </footer>
  );
}
