import { useEffect, useRef, useState } from 'react';
import { api } from '../api/client';
import { useToast } from '../store/ToastContext';

function traduzirRecusa(detail) {
  const mapa = {
    cc_rejected_bad_filled_card_number: 'Número do cartão inválido. Confira os dados.',
    cc_rejected_bad_filled_date: 'Data de validade inválida.',
    cc_rejected_bad_filled_security_code: 'Código de segurança (CVV) inválido.',
    cc_rejected_bad_filled_other: 'Confira os dados do cartão.',
    cc_rejected_insufficient_amount: 'Saldo ou limite insuficiente.',
    cc_rejected_high_risk: 'Banco recusou (alto risco). Tente outro cartão.',
    cc_rejected_call_for_authorize: 'O banco pede autorização. Fale com o banco ou tente outro cartão.',
    cc_rejected_duplicated_payment: 'Pagamento duplicado detectado.',
    cc_rejected_card_disabled: 'Cartão desabilitado. Fale com o banco.',
    cc_rejected_blacklist: 'Cartão bloqueado. Tente outro cartão.',
    cc_rejected_other_reason: 'Banco recusou. Tente outro cartão ou o Pix.',
  };
  return mapa[detail] || `Pagamento recusado${detail ? ` (${detail})` : ''}. Tente outro cartão ou o Pix.`;
}

function desmontarBrick(ctrl) {
  // unmount() do Brick pode retornar undefined (não é promise): nunca
  // encadear .catch direto — o TypeError derrubava o React (tela branca).
  try {
    const r = ctrl?.unmount?.();
    if (r && typeof r.catch === 'function') r.catch(() => {});
  } catch { /* ignore */ }
}

function loadMpSdk() {

  if (window.MercadoPago) return Promise.resolve();
  return new Promise((resolve, reject) => {
    const s = document.createElement('script');
    s.src = 'https://sdk.mercadopago.com/js/v2';
    s.onload = resolve;
    s.onerror = () => reject(new Error('SDK bloqueado — desative AdBlock para este site'));
    document.head.appendChild(s);
  });
}

export default function PaymentModal({ order, onClose, onSuccess }) {
  const { toast } = useToast();
  const [estado, setEstado] = useState('loading'); // loading | form | pix | erro
  const [mensagem, setMensagem] = useState('Carregando pagamento...');
  const [pix, setPix] = useState(null);
  const [verificando, setVerificando] = useState(false);
  const brickCtrl = useRef(null);
  const initializing = useRef(false);

  // Polling do Pix: confere no Mercado Pago a cada 5s (até 10 min).
  // Funciona mesmo se o webhook falhar — a confirmação vem da consulta.
  const checarPagamento = async (paymentId) => {
    if (!paymentId || verificando) return false;
    setVerificando(true);
    try {
      const st = await api.getPaymentStatus(paymentId);
      const pay = String(st.payment_status || '').toLowerCase();
      const ped = String(st.pedido_status || '').toLowerCase();
      if (pay === 'approved' || ped === 'pago') {
        onSuccess(order);
        return true;
      }
      if (['rejected', 'cancelled', 'expired'].includes(pay)) {
        setEstado('erro');
        setMensagem(pay === 'expired' ? 'Pix expirado. Gere um novo pagamento.' : 'Pagamento não aprovado. Tente novamente.');
        return true;
      }
    } catch (e) {
      toast(e.message, 'error');
    } finally {
      setVerificando(false);
    }
    return false;
  };

  useEffect(() => {
    const pixId = pix?.id || pix?.payment_id;
    if (estado !== 'pix' || !pixId) return;
    let tentativas = 0;
    const id = setInterval(async () => {
      tentativas += 1;
      if (tentativas > 120) {
        clearInterval(id);
        return;
      }
      if (await checarPagamento(pixId)) clearInterval(id);
    }, 5000);
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [estado, pix?.id, pix?.payment_id]);

  useEffect(() => {
    if (!order) return;
    let cancelado = false;

    (async () => {
      if (initializing.current) return;
      initializing.current = true;
      setEstado('loading');
      setMensagem('Carregando opções de pagamento...');
      try {
        const valor = Number(order.valorTotal);
        if (!valor || valor <= 0) throw new Error('Valor do pedido inválido. Refaça o pedido.');
        const user = api.getUser();
        const email = user?.username?.includes('@') ? user.username : 'comprador@email.com';
        const pkData = await api.getPublicKey().catch(() => ({ public_key: '' }));
        const pk = String(pkData.public_key || '').trim();
        if (!pk || !/^(TEST|APP_USR)-/.test(pk)) {
          throw new Error('Pagamento indisponível: chave pública não configurada no servidor.');
        }
        await loadMpSdk();
        if (cancelado) return;
        const mp = new window.MercadoPago(pk, { locale: 'pt-BR' });
        if (brickCtrl.current) {
          desmontarBrick(brickCtrl.current);
          brickCtrl.current = null;
        }
        setEstado('form');
        // Aguarda o container existir no DOM
        await new Promise((r) => setTimeout(r, 60));
        const criar = mp.bricks().create('payment', 'brick_container_react', {
          initialization: { amount: valor, payer: { email } },
          customization: { paymentMethods: { ticket: 'all', bankTransfer: 'all', creditCard: 'all', debitCard: 'all' } },
          callbacks: {
            onReady: () => {},
            onSubmit: async ({ selectedPaymentMethod, formData }) => {
              const metodo = formData.payment_method_id || selectedPaymentMethod;
              const payerBrick = { ...(formData?.payer || {}), email: formData?.payer?.email || email };
              const idempotencyKey = `pedido-${order.idPedido}-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
              try {
                const res = await api.processPayment(order.idPedido, { ...formData, payment_method_id: metodo, payer: payerBrick }, idempotencyKey);
                if (res.qr_code_base64) {
                  setPix(res);
                  setEstado('pix');
                  return new Promise(() => {});
                }
                const st = String(res.status || '').toLowerCase();
                if (['approved', 'authorized'].includes(st)) {
                  onSuccess(order);
                } else if (['in_process', 'pending'].includes(st)) {
                  toast('Pagamento em análise. A confirmação chega automaticamente.', 'info');
                } else {
                  toast(traduzirRecusa(res.status_detail), 'error');
                  setTimeout(() => window.location.reload(), 1200);
                }
              } catch (e) {
                toast(e.message, 'error');
              }
              return new Promise(() => {});
            },
            onError: (e) => {
              console.error('brick error', e);
              toast('Erro ao carregar o pagamento. Tente novamente.', 'error');
            },
          },
        });
        const timeout = new Promise((_, rej) => setTimeout(() => rej(new Error('Tempo esgotado (15s)')), 15000));
        brickCtrl.current = await Promise.race([criar, timeout]);
      } catch (e) {
        if (!cancelado) {
          setEstado('erro');
          setMensagem(e.message || 'Falha ao carregar pagamento.');
          toast(e.message || 'Falha ao carregar pagamento.', 'error');
        }
      } finally {
        initializing.current = false;
      }
    })();

    return () => {
      cancelado = true;
      if (brickCtrl.current) {
        desmontarBrick(brickCtrl.current);
        brickCtrl.current = null;
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [order?.idPedido]);

  if (!order) return null;
  return (
    <div className="modal-overlay show" onClick={onClose}>
      <div className="modal modal-wide" onClick={(e) => e.stopPropagation()}>
        <div className="drawer-head">
          <h2>Pagamento seguro</h2>
          <button className="icon-btn" onClick={onClose}>✕</button>
        </div>
        <div className="drawer-body" style={{ textAlign: 'center' }}>
          <p className="modal-text" style={{ marginBottom: 12 }}>
            {order.protocolo ? <>Pedido <b>{order.protocolo}</b> • </> : null}Total <b>{api.formatarMoeda(order.valorTotal)}</b>
            {order.entrega_tipo ? ` • ${order.entrega_tipo}` : ''}
          </p>
          {estado === 'loading' && <div className="spinner" />}
          {estado === 'erro' && (
            <div className="notice notice-warn">{mensagem}<br /><br /><button className="btn btn-primary btn-sm" onClick={() => window.location.reload()}>Tentar novamente</button></div>
          )}
          <div id="brick_container_react" className="brick-box" style={{ display: estado === 'pix' ? 'none' : 'block' }} />
          {estado === 'pix' && pix && (
            <div>
              <div className="notice notice-ok">📱 Escaneie o QR Code no app do banco para concluir.</div>
              {pix.qr_code_base64 && <img className="pix-qr" src={`data:image/png;base64,${pix.qr_code_base64}`} alt="QR Pix" />}
              {pix.qr_code && (
                <>
                  <div className="pix-code">{pix.qr_code}</div>
                  <button className="btn btn-outline btn-sm" onClick={() => { navigator.clipboard.writeText(pix.qr_code); toast('Código Pix copiado!', 'success'); }}>Copiar código Pix</button>
                </>
              )}
              <p className="form-hint" style={{ marginTop: 10 }}>Após pagar, o pedido é confirmado automaticamente. Acompanhe em Minhas Compras.</p>
              <button className="btn btn-primary btn-sm" style={{ marginTop: 8 }} disabled={verificando} onClick={() => checarPagamento(pix.id || pix.payment_id)}>
                {verificando ? 'Verificando…' : 'Já paguei — verificar agora'}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
