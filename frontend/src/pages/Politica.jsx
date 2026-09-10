import { Link } from 'react-router-dom';

export default function Politica() {
  return (
    <main>
      <div className="page-hero"><div className="container">
        <h1>Política de Privacidade</h1>
        <p>Como tratamos seus dados na JP Croco.</p>
      </div></div>
      <div className="container" style={{ paddingBottom: 48 }}>
        <div className="card" style={{ padding: 28, maxWidth: 820 }}>
          <h3>Coleta de dados</h3>
          <p style={{ color: 'var(--cinza-500)', fontSize: '.92rem', margin: '8px 0 16px' }}>
            Coletamos nome, email, telefone, CPF e endereço de entrega para processar pedidos, calcular frete,
            processar pagamentos via Mercado Pago e viabilizar a entrega via Correios ou entrega local (DF).
          </p>
          <h3>Uso e compartilhamento</h3>
          <p style={{ color: 'var(--cinza-500)', fontSize: '.92rem', margin: '8px 0 16px' }}>
            Seus dados são usados apenas para a operação da loja: pagamento, emissão de rastreio e comunicação
            sobre o pedido (email/WhatsApp). Não vendemos seus dados.
          </p>
          <h3>Seus direitos</h3>
          <p style={{ color: 'var(--cinza-500)', fontSize: '.92rem', margin: '8px 0 16px' }}>
            Você pode solicitar correção ou exclusão dos seus dados a qualquer momento pelo email contato@jpcroco.com.br.
          </p>
          <Link to="/" className="btn btn-primary btn-sm">Voltar à loja</Link>
        </div>
      </div>
    </main>
  );
}
