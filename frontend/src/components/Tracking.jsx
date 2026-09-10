import { useState } from 'react';
import { api, VENDEDOR_WHATSAPP } from '../api/client';
import { useToast } from '../store/ToastContext';

const STEPS = [
  { id: 1, label: 'Postado' },
  { id: 2, label: 'Em Trânsito' },
  { id: 3, label: 'Saiu p/ Entrega' },
  { id: 4, label: 'Entregue' },
];

function fmtData(d) {
  if (!d) return '';
  try {
    const dt = new Date(d);
    return dt.toLocaleDateString('pt-BR', { day: '2-digit', month: 'short' });
  } catch {
    return '';
  }
}

export function badgeClass(status) {
  const s = String(status || '').toLowerCase();
  if (s === 'pago') return 'badge-pago';
  if (s === 'enviado') return 'badge-enviado';
  if (s === 'entregue') return 'badge-entregue';
  if (['recusado', 'cancelado', 'cancelled'].includes(s)) return 'badge-recusado';
  return 'badge-pendente';
}

export function whatsappPedido(pedido, nome) {
  const idp = pedido.id_pedido || 'em processamento';
  const tipo = pedido.entrega_tipo || '';
  const msg = tipo.includes('Retirada')
    ? `Olá! Meu pedido ${idp} é Retirada na loja. Meu nome é ${nome}. Poderia me enviar o endereço da loja? Pedido: ${idp}`
    : `Olá! Meu pedido ${idp} é Entrega via Uber. Meu nome é ${nome}, meu endereço é ${pedido.endereco_entrega}, tipo: ${tipo}. Pedido: ${idp}`;
  window.open(`https://wa.me/${VENDEDOR_WHATSAPP}?text=${encodeURIComponent(msg)}`, '_blank');
}

export default function TrackingBox({ pedido }) {
  const { toast } = useToast();
  const [aberto, setAberto] = useState(false);
  const [loading, setLoading] = useState(false);
  const [dados, setDados] = useState(null);

  const isLocal = pedido.entrega_tipo?.includes('Retirada') || pedido.entrega_tipo?.includes('Uber');

  const consultar = async () => {
    if (!pedido.codigo_rastreio) return;
    if (aberto) { setAberto(false); return; }
    setAberto(true);
    setLoading(true);
    try {
      const res = await api.rastrear(pedido.codigo_rastreio);
      setDados(res);
    } catch (e) {
      toast(e.message, 'error');
    } finally {
      setLoading(false);
    }
  };

  if (!pedido.codigo_rastreio && !isLocal) {
    return (
      <div className="track-box" style={{ background: 'var(--warn-bg)' }}>
        <b>⏳ Aguardando envio</b>
        <p style={{ fontSize: '.85rem', color: 'var(--cinza-500)', marginTop: 4 }}>
          Pagamento confirmado. Assim que despacharmos pelos Correios, o código de rastreio aparece aqui.
        </p>
      </div>
    );
  }
  if (!pedido.codigo_rastreio) return null;

  const steps = dados?.steps?.length ? dados.steps : STEPS.map((s) => ({ ...s, ativo: false, data: null }));
  const eventos = dados?.eventos || [];

  return (
    <div className="track-box">
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10, flexWrap: 'wrap', alignItems: 'center' }}>
        <div>
          <small style={{ color: 'var(--cinza-500)' }}>Transportadora • {pedido.transportadora || 'Correios'}</small><br />
          <span className="code-pill">
            {pedido.codigo_rastreio}
            <button onClick={() => { navigator.clipboard.writeText(pedido.codigo_rastreio); toast('Código copiado!', 'success'); }} style={{ color: '#fff', textDecoration: 'underline', fontSize: '.75rem' }}>Copiar</button>
          </span>
        </div>
        <button className="btn btn-primary btn-sm" onClick={consultar}>📍 {aberto ? 'Ocultar' : 'Rastrear em tempo real'}</button>
      </div>
      {aberto && (
        <div style={{ marginTop: 12 }}>
          {loading ? <div className="spinner" /> : (
            <>
              <div className="stepper">
                {steps.map((s) => (
                  <div key={s.id} className={`step${s.ativo ? ' done' : ''}`}>
                    <div className="step-dot" />
                    <div className="step-line" />
                    <div className="step-label">{s.label}</div>
                    <div className="step-date">{s.data ? fmtData(s.data) : ''}</div>
                  </div>
                ))}
              </div>
              {dados?.aviso && <p className="form-hint">ℹ️ {dados.aviso}</p>}
              <div className="timeline">
                {eventos.slice(0, 6).map((e, i) => (
                  <div className="tl-item" key={i}>
                    <b>{e.descricao || e.status || 'Evento'}</b>
                    <div style={{ color: 'var(--cinza-500)', fontSize: '.78rem' }}>
                      {e.dtHrCriado || e.data || ''} {e.unidade?.local || e.local || ''}
                    </div>
                    {(e.detalhe || e.complemento) && <div>{e.detalhe || e.complemento}</div>}
                  </div>
                ))}
                {!eventos.length && <div className="tl-item">Nenhum evento ainda — tente em instantes.</div>}
              </div>
              <p className="form-hint" style={{ marginTop: 8 }}>
                Ou acompanhe direto no <a href="https://www2.correios.com.br/sistemas/rastreamento/" target="_blank" rel="noreferrer" style={{ textDecoration: 'underline' }}>site dos Correios</a>.
              </p>
            </>
          )}
        </div>
      )}
    </div>
  );
}
