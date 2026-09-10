import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import { useAuth } from '../store/AuthContext';
import { useCart } from '../store/CartContext';
import { useToast } from '../store/ToastContext';

const UFS = ['AC','AL','AP','AM','BA','CE','DF','ES','GO','MA','MT','MS','MG','PA','PB','PR','PE','PI','RJ','RN','RS','RO','RR','SC','SP','SE','TO'];

function onlyDigits(s) { return String(s || '').replace(/\D/g, ''); }
function maskCep(v) {
  const d = onlyDigits(v).slice(0, 8);
  return d.length > 5 ? `${d.slice(0, 5)}-${d.slice(5)}` : d;
}

export default function CheckoutModal({ open, onClose, onPaid }) {
  const { user } = useAuth();
  const { arr, subtotal, limpar } = useCart();
  const { toast } = useToast();
  const navigate = useNavigate();

  const [cliente, setCliente] = useState(null);
  const [loadingCliente, setLoadingCliente] = useState(false);
  const [rua, setRua] = useState('');
  const [numero, setNumero] = useState('');
  const [complemento, setComplemento] = useState('');
  const [cidade, setCidade] = useState('');
  const [estado, setEstado] = useState('');
  const [cep, setCep] = useState('');
  const [buscandoCep, setBuscandoCep] = useState(false);
  const [freteOpcoes, setFreteOpcoes] = useState([]);
  const [freteValor, setFreteValor] = useState(0);
  const [entregaTipo, setEntregaTipo] = useState('');
  const [freteInfo, setFreteInfo] = useState(null);
  const [calculando, setCalculando] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const [erros, setErros] = useState({});

  const total = useMemo(() => subtotal + (Number(freteValor) || 0), [subtotal, freteValor]);

  // Carrega cliente vinculado (dados pessoais vêm da conta — igual ao fluxo antigo)
  useEffect(() => {
    if (!open) return;
    (async () => {
      setLoadingCliente(true);
      try {
        let c = null;
        if (user?.username?.includes('@')) c = await api.getClienteByEmail(user.username).catch(() => null);
        if (!c) {
          const all = await api.getClientes({ limit: 100 }).catch(() => null);
          const lista = all?.clientes || [];
          c = lista.find((x) => x.email === user?.username)
            || lista.find((x) => x.email?.toLowerCase() === String(user?.username || '').toLowerCase()) || null;
        }
        setCliente(c);
      } finally {
        setLoadingCliente(false);
      }
    })();
  }, [open, user]);

  const buscarCep = async (valor) => {
    const d = onlyDigits(valor);
    if (d.length !== 8) return;
    setBuscandoCep(true);
    try {
      const end = await api.consultarCep(d);
      if (end.rua) setRua(end.rua);
      if (end.cidade) setCidade(end.cidade);
      if (end.estado) setEstado(end.estado);
      toast('Endereço preenchido pelo CEP.', 'success');
    } catch (e) {
      toast(e.message, 'error');
    } finally {
      setBuscandoCep(false);
    }
  };

  const calcularFrete = async () => {
    const d = onlyDigits(cep);
    if (d.length !== 8) {
      toast('Informe um CEP válido com 8 dígitos.', 'error');
      return;
    }
    setCalculando(true);
    setFreteOpcoes([]);
    setFreteValor(0);
    try {
      const itens = arr.map((i) => ({ peso_gramas: 500, comprimento: 20, largura: 15, altura: 10, quantidade: i.quantidade }));
      const res = await api.calcularFrete({ cepDestino: d, itens });
      const opcoes = res.opcoes || [];
      setFreteOpcoes(opcoes);
      setFreteInfo(res);
      if (opcoes.length) {
        setFreteValor(Number(opcoes[0].valor) || 0);
        setEntregaTipo(opcoes[0].servico);
      }
      if (res.entregaLocal) toast('Para DF e Entorno: retirada grátis ou Uber a combinar.', 'info');
    } catch (e) {
      toast(`Frete: ${e.message}`, 'error');
    } finally {
      setCalculando(false);
    }
  };

  useEffect(() => {
    if (open && onlyDigits(cep).length === 8 && arr.length) {
      const t = setTimeout(() => { buscarCep(cep); calcularFrete(); }, 600);
      return () => clearTimeout(t);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cep]);

  const validar = () => {
    const e = {};
    if (!rua.trim()) e.rua = true;
    if (!numero.trim()) e.numero = true;
    if (!cidade.trim()) e.cidade = true;
    if (!estado) e.estado = true;
    if (onlyDigits(cep).length !== 8) e.cep = true;
    if (!freteOpcoes.length) e.frete = true;
    if (!entregaTipo) e.frete = true;
    setErros(e);
    return Object.keys(e).length === 0;
  };

  const confirmar = async () => {
    if (enviando) return;
    if (!cliente?.nome || !cliente?.telefone || !cliente?.cpf) {
      toast("Cadastre seus dados pessoais em 'Minha Conta' para comprar.", 'error');
      onClose();
      navigate('/conta');
      return;
    }
    if (!validar()) {
      if (!freteOpcoes.length) toast('Calcule o frete pelo CEP antes de confirmar.', 'error');
      return;
    }
    setEnviando(true);
    try {
      const endereco = `${rua.trim()}, ${numero.trim()}${complemento.trim() ? ` - ${complemento.trim()}` : ''}, ${cidade.trim()} - ${estado}, CEP: ${maskCep(cep)}`;
      const pedido = await api.createPedido({
        cliente_id: cliente.id,
        status: 'pendente',
        endereco_entrega: endereco,
        valor_total: Number(total.toFixed(2)),
        entrega_tipo: entregaTipo,
        valor_frete: Number(Number(freteValor).toFixed(2)),
        subtotal: Number(subtotal.toFixed(2)),
        cep_destino: maskCep(cep),
      });
      for (const item of arr) {
        const payload = { pedido_id: pedido.id, produto_id: item.produto_id, quantidade: item.quantidade, preco_unitario: item.preco };
        if (item.tamanho) payload.tamanho = item.tamanho;
        await api.createItemPedido(payload);
      }
      try {
        localStorage.setItem('ultimo_pedido', JSON.stringify({
          id: pedido.id, id_pedido: pedido.id_pedido, valor_total: Number(total.toFixed(2)),
          entrega_tipo: entregaTipo, endereco_entrega: endereco,
        }));
      } catch { /* ignore */ }
      limpar();
      onClose();
      onPaid({ idPedido: pedido.id, protocolo: pedido.id_pedido, valorTotal: Number(total.toFixed(2)), entrega_tipo: entregaTipo });
    } catch (e) {
      toast(e.message, 'error');
    } finally {
      setEnviando(false);
    }
  };

  if (!open) return null;
  return (
    <div className="modal-overlay show" onClick={onClose}>
      <div className="modal modal-wide" onClick={(e) => e.stopPropagation()} style={{ textAlign: 'left' }}>
        <div className="drawer-head">
          <h2>Finalizar Compra</h2>
          <button className="icon-btn" onClick={onClose}>✕</button>
        </div>
        <div className="drawer-body">
          {loadingCliente ? (
            <div className="spinner" />
          ) : !cliente?.nome || !cliente?.telefone || !cliente?.cpf ? (
            <div className="notice notice-warn">
              Complete seus dados pessoais em <b>Minha Conta</b> antes de comprar.
              <br /><br />
              <button className="btn btn-primary btn-sm" onClick={() => { onClose(); navigate('/conta'); }}>Ir para Minha Conta</button>
            </div>
          ) : (
            <div className="notice notice-ok">Comprando como <b>{cliente.nome}</b> • {cliente.email} • dados da sua conta.</div>
          )}

          <div className="checkout-section">
            <h3>📍 Endereço de entrega</h3>
            <div className="form-row">
              <div className={`form-group${erros.cep ? ' invalid' : ''}`}>
                <label className="form-label">CEP *</label>
                <input value={cep} onChange={(e) => setCep(maskCep(e.target.value))} onBlur={(e) => buscarCep(e.target.value)} placeholder="00000-000" inputMode="numeric" />
                <span className="form-error-msg">CEP inválido</span>
              </div>
              <div className={`form-group${erros.cidade ? ' invalid' : ''}`}>
                <label className="form-label">Cidade *</label>
                <input value={cidade} onChange={(e) => setCidade(e.target.value)} placeholder="Sua cidade" />
                <span className="form-error-msg">Preencha a cidade</span>
              </div>
            </div>
            <div className="form-row">
              <div className={`form-group${erros.rua ? ' invalid' : ''}`}>
                <label className="form-label">Rua / Logradouro *</label>
                <input value={rua} onChange={(e) => setRua(e.target.value)} placeholder="Rua, Avenida..." />
                <span className="form-error-msg">Preencha o endereço</span>
              </div>
              <div className={`form-group${erros.numero ? ' invalid' : ''}`}>
                <label className="form-label">Número *</label>
                <input value={numero} onChange={(e) => setNumero(e.target.value)} placeholder="123" />
                <span className="form-error-msg">Preencha o número</span>
              </div>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label className="form-label">Complemento</label>
                <input value={complemento} onChange={(e) => setComplemento(e.target.value)} placeholder="Apto, Bloco..." />
              </div>
              <div className={`form-group${erros.estado ? ' invalid' : ''}`}>
                <label className="form-label">Estado *</label>
                <select value={estado} onChange={(e) => setEstado(e.target.value)}>
                  <option value="">Selecione</option>
                  {UFS.map((u) => <option key={u} value={u}>{u}</option>)}
                </select>
                <span className="form-error-msg">Selecione o estado</span>
              </div>
            </div>
            {buscandoCep && <p className="form-hint">🔎 Buscando endereço pelo CEP...</p>}
          </div>

          <div className="checkout-section">
            <h3>🚚 Opções de entrega</h3>
            <button className="btn btn-outline btn-sm" onClick={calcularFrete} disabled={calculando || onlyDigits(cep).length !== 8}>
              {calculando ? 'Calculando...' : '📦 Calcular frete pelo CEP'}
            </button>
            {freteInfo && (
              <p className="form-hint" style={{ marginTop: 8 }}>
                Peso real {freteInfo.pesoReal ?? '—'}g • Cubado {freteInfo.pesoCubadoKg ?? '—'}kg • Taxável {freteInfo.pesoTaxavel ?? '—'}g
                {freteInfo.mock ? ' • (simulação — sem credencial dos Correios)' : ''}
              </p>
            )}
            <div className="frete-box" style={{ display: freteOpcoes.length ? 'block' : 'none' }}>
              {freteOpcoes.map((o) => (
                <button
                  key={o.servico}
                  className={`frete-opt${entregaTipo === o.servico ? ' selected' : ''}`}
                  onClick={() => { setFreteValor(Number(o.valor) || 0); setEntregaTipo(o.servico); }}
                >
                  <span>
                    <input type="radio" readOnly checked={entregaTipo === o.servico} style={{ width: 'auto', marginRight: 8 }} />
                    <b>{o.servico}</b>{o.prazo ? ` • ${o.prazo} dias úteis` : ''}
                    {o.obs && <small>{o.obs}</small>}
                  </span>
                  <b>{o.valor === 0 && o.coProduto === 'UBER' ? 'A combinar' : api.formatarMoeda(o.valor)}</b>
                </button>
              ))}
            </div>
            {erros.frete && <p className="form-hint" style={{ color: 'var(--erro)' }}>Selecione uma opção de entrega (calcule pelo CEP).</p>}
          </div>
        </div>
        <div className="drawer-foot">
          <div className="summary-row"><span>Subtotal ({arr.length} itens)</span><span>{api.formatarMoeda(subtotal)}</span></div>
          <div className="summary-row"><span>Frete{entregaTipo ? ` • ${entregaTipo}` : ''}</span><span>{freteOpcoes.length ? (Number(freteValor) === 0 && entregaTipo.includes('Uber') ? 'A combinar' : api.formatarMoeda(freteValor)) : '—'}</span></div>
          <div className="summary-row total"><span>Total</span><span>{api.formatarMoeda(total)}</span></div>
          <button className="btn btn-primary btn-block" onClick={confirmar} disabled={enviando || !arr.length}>
            {enviando ? 'Criando pedido...' : 'Confirmar Pedido e Pagar'}
          </button>
          <p className="form-hint" style={{ textAlign: 'center', marginTop: 8 }}>Após confirmar, o pagamento abre em janela segura do Mercado Pago.</p>
        </div>
      </div>
    </div>
  );
}
