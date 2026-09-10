import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import { useAuth } from '../store/AuthContext';
import { useToast } from '../store/ToastContext';
import { useAdminNotify } from '../hooks/useAdminNotify';

const TABS = [['dashboard', '📊 Dashboard'], ['produtos', '🐊 Produtos'], ['pedidos', '📦 Pedidos'], ['usuarios', '👥 Usuários'], ['clientes', '🧑 Clientes'], ['admins', '🔑 Admins']];
const PED_ABAS = [['todos', 'Todos'], ['pendente', 'Pendente'], ['pago', 'Pago'], ['enviado', 'Enviado'], ['entregue', 'Entregue'], ['recusado', 'Recusado']];

const NOMES_STATUS = {
  pago: 'Pagamento aprovado ✅', aprovado: 'Pagamento aprovado ✅', approved: 'Pagamento aprovado ✅',
  enviado: 'Pedido enviado 📦', entregue: 'Pedido entregue ✔',
  recusado: 'Pedido recusado ✕', cancelado: 'Pedido cancelado ✕', cancelled: 'Pedido cancelado ✕',
  pendente: 'Aguardando pagamento ⏳',
};

function matchAba(p, aba) {
  const s = String(p.status || '').toLowerCase();
  if (aba === 'todos') return true;
  if (aba === 'pendente') return s === 'pendente';
  if (aba === 'pago') return ['pago', 'aprovado', 'approved'].includes(s);
  if (aba === 'enviado') return s === 'enviado';
  if (aba === 'entregue') return s === 'entregue';
  if (aba === 'recusado') return ['recusado', 'cancelado', 'cancelled'].includes(s);
  return true;
}

export default function Admin() {
  const { user } = useAuth();
  const { toast } = useToast();
  const navigate = useNavigate();
  const [tab, setTab] = useState('dashboard');
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState(null);
  const [produtos, setProdutos] = useState([]);
  const [pedidos, setPedidos] = useState([]);
  const [usuarios, setUsuarios] = useState([]);
  const [clientes, setClientes] = useState([]);
  const [admins, setAdmins] = useState([]);
  const [aba, setAba] = useState('todos');
  const [busca, setBusca] = useState('');
  const [buscaProd, setBuscaProd] = useState('');
  const [modal, setModal] = useState(null); // {tipo:'produto'|'pedido'|'usuario'|'cliente', dados}
  const [pollNovas, setPollNovas] = useState(0);
  const [autoReload, setAutoReload] = useState(true);
  const [restante, setRestante] = useState(60);
  const snapRef = useRef({}); // snapshot de status p/ detectar mudanças (e não auto-notificar a própria edição)
  const notify = useAdminNotify();
  const [ alternando, setAlternando ] = useState(false);

  useEffect(() => {
    if (user && user.acesso !== 'admin') navigate('/', { replace: true });
    else if (!user) navigate('/login', { replace: true });
  }, [user, navigate]);

  const carregar = async (qual = tab, opts = {}) => {
    if (!opts.silent) setLoading(true);
    try {
      if (qual === 'dashboard') {
        const [pr, pe, us, cl] = await Promise.all([
          api.getProdutos({ limit: 1000 }), api.getPedidos({ limit: 1000 }),
          api.getUsuarios({ limit: 1000 }), api.getClientes({ limit: 1000 }).catch(() => ({ clientes: [] })),
        ]);
        setProdutos(pr.produtos || []);
        setPedidos(pe.pedidos || []);
        setStats({
          produtos: pr.produtos?.length || 0, pedidos: pe.pedidos?.length || 0,
          usuarios: us.usuarios?.length || 0, clientes: cl.clientes?.length || 0,
          receita: (pe.pedidos || []).reduce((s, p) => s + (Number(p.valor_total) || 0), 0),
          pendentes: (pe.pedidos || []).filter((p) => p.status === 'pendente').length,
        });
      }
      if (qual === 'produtos') setProdutos((await api.getProdutos({ limit: 1000 })).produtos || []);
      if (qual === 'pedidos') setPedidos((await api.getPedidos({ limit: 1000 })).pedidos || []);
      if (qual === 'usuarios') setUsuarios((await api.getUsuarios({ limit: 1000 })).usuarios || []);
      if (qual === 'clientes') setClientes((await api.getClientes({ limit: 1000 }).catch(() => ({ clientes: [] }))).clientes || []);
      if (qual === 'admins') setAdmins((await api.getAdmins({ limit: 1000 }).catch(() => ({ admins: [] }))).admins || []);
    } catch (e) {
      toast(e.message, 'error');
    } finally {
      if (!opts.silent) setLoading(false);
    }
  };

  useEffect(() => { if (user?.acesso === 'admin') carregar(tab); /* eslint-disable-next-line */ }, [tab]);

  // Auto-reload da aba atual a cada 60s (silencioso, sem spinner). Não
  // recarrega no meio de edição: modal aberta ou digitando em campo — nesse
  // caso apenas reinicia a contagem e tenta de novo no próximo ciclo.
  const tabRef = useRef(tab);
  tabRef.current = tab;
  const modalRef = useRef(modal);
  modalRef.current = modal;
  const autoRef = useRef(autoReload);
  autoRef.current = autoReload;
  const carregarRef = useRef(carregar);
  carregarRef.current = carregar;
  useEffect(() => {
    const id = setInterval(() => {
      if (!autoRef.current) return;
      setRestante((r) => {
        if (r > 1) return r - 1;
        const foco = document.activeElement;
        const editando = modalRef.current || (foco && ['INPUT', 'TEXTAREA', 'SELECT'].includes(foco.tagName));
        if (!editando) carregarRef.current(tabRef.current, { silent: true });
        return 60;
      });
    }, 1000);
    return () => clearInterval(id);
  }, []);

  const alternarReload = () => {
    setAutoReload((v) => !v);
    setRestante(60);
  };

  // Poll de pedidos: a cada mudança de STATUS notifica em dois lugares —
  // 1) no PAINEL (toast) e 2) no APARELHO do admin logado (notificação do
  // sistema + som + vibração). Mudanças vindas de outro aparelho/sessão
  // chegam também por push do backend, mesmo com o site fechado.
  useEffect(() => {
    if (user?.acesso !== 'admin') return;
    snapRef.current = {};
    const id = setInterval(async () => {
      try {
        const d = await api.getPedidos({ limit: 1000 });
        const lista = d.pedidos || [];
        const snap = snapRef.current;
        const primeira = Object.keys(snap).length === 0;
        const eventos = [];
        lista.forEach((p) => {
          const st = String(p.status || '').toLowerCase();
          const idp = p.id_pedido || `#${p.id}`;
          if (!(p.id in snap)) {
            if (!primeira) eventos.push(['🛒 Nova compra!', `Pedido ${idp} • ${p.status} • ${api.formatarMoeda(p.valor_total)}`]);
          } else if (snap[p.id] !== st) {
            eventos.push(['🔔 Atualização de pedido', `Pedido ${idp}: ${NOMES_STATUS[st] || p.status}`]);
          }
          snap[p.id] = st;
        });
        if (eventos.length > 0) {
          setPollNovas((n) => n + eventos.length);
          eventos.forEach(([titulo, corpo]) => {
            toast(`${titulo} — ${corpo}`, 'success');
            notify.notificarAparelho(titulo, corpo);
          });
          if (tab === 'pedidos' || tab === 'dashboard') carregar(tab);
        }
      } catch { /* ignore */ }
    }, 15000);
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab]);

  const trocarTab = (t) => { setTab(t); setPollNovas(0); };

  const salvarPedido = async (idPedido, payload) => {
    try {
      if (payload.codigo_rastreio && String(payload.codigo_rastreio).trim().length < 8) {
        return toast('Código de rastreio inválido (mínimo 8 caracteres).', 'error');
      }
      await api.updatePedido(idPedido, payload);
      toast(payload.codigo_rastreio ? 'Código salvo! Cliente notificado automaticamente.' : 'Pedido atualizado!', 'success');
      // Sincroniza o snapshot p/ não gerar auto-notificação da própria edição;
      // o backend empurra push aos demais aparelhos mesmo assim.
      try {
        const editado = pedidos.find((p) => String(p.id_pedido || p.id) === String(idPedido));
        const novoStatus = String(payload.status || editado?.status || 'enviado').toLowerCase();
        if (editado) snapRef.current[editado.id] = novoStatus;
        else {
          const d = await api.getPedidos({ limit: 1000 }).catch(() => null);
          (d?.pedidos || []).forEach((p) => { snapRef.current[p.id] = String(p.status || '').toLowerCase(); });
        }
      } catch { /* ignore */ }
      setModal(null);
      carregar('pedidos');
    } catch (e) {
      toast(e.message, 'error');
    }
  };

  const salvarProduto = async (id, dados) => {
    try {
      if (id) await api.updateProduto(id, dados);
      else await api.createProduto(dados);
      toast(id ? 'Produto atualizado!' : 'Produto criado!', 'success');
      setModal(null);
      carregar('produtos');
    } catch (e) {
      toast(e.message, 'error');
    }
  };

  const pedidosFiltrados = pedidos.filter((p) => matchAba(p, aba)
    && (!busca.trim() || String(p.id_pedido || p.id).toLowerCase().includes(busca.toLowerCase()) || String(p.cliente_id).includes(busca)));
  const prodsFiltrados = produtos.filter((p) => !buscaProd.trim() || p.nome.toLowerCase().includes(buscaProd.toLowerCase()));

  return (
    <div className="admin-layout">
      <nav className="admin-nav">
        {TABS.map(([v, l]) => (
          <button key={v} className={tab === v ? 'active' : ''} onClick={() => trocarTab(v)}>
            {l}{v === 'pedidos' && pollNovas > 0 ? ` (${pollNovas})` : ''}
          </button>
        ))}
      </nav>
      <div className="admin-content">
        <NotifyBar notify={notify} trabalhando={alternando} autoReload={autoReload} restante={restante} onToggleReload={alternarReload} onAlternar={async () => {
          setAlternando(true);
          try {
            if (notify.preferencia === '0') {
              const r = await notify.ativar();
              if (r === 'ok') toast('Aparelho inscrito: você será avisado aqui e no sistema.', 'success');
              else if (r === 'sem-push') toast('Painel avisa normalmente; push com site fechado indisponível (sem chave VAPID/HTTPS).', 'info');
              else if (r === 'bloqueado') toast('Notificações bloqueadas no navegador. Ative nas configurações do site.', 'error');
              else if (r === 'painel') toast('Este navegador não suporta notificação no aparelho; o painel continua avisando.', 'info');
            } else {
              await notify.desativar();
              toast('Notificações do aparelho pausadas (painel continua avisando).', 'info');
            }
          } finally {
            setAlternando(false);
          }
        }} />
        {loading ? <div className="spinner" /> : (
          <>
            {tab === 'dashboard' && stats && (
              <>
                <div className="stat-grid">
                  <div className="stat"><small>Produtos</small><b>{stats.produtos}</b></div>
                  <div className="stat"><small>Pedidos ({stats.pendentes} pendentes)</small><b>{stats.pedidos}</b></div>
                  <div className="stat"><small>Receita Total</small><b>{api.formatarMoeda(stats.receita)}</b></div>
                  <div className="stat"><small>Clientes / Usuários</small><b>{stats.clientes} / {stats.usuarios}</b></div>
                </div>
                <div className="card">
                  <div className="card-head"><h3>Pedidos Recentes</h3><button className="mini-btn" onClick={() => trocarTab('pedidos')}>Ver todos</button></div>
                  <TabelaPedidos lista={pedidos.slice(-5).reverse()} onEdit={(p) => setModal({ tipo: 'pedido', dados: p })} />
                </div>
              </>
            )}

            {tab === 'produtos' && (
              <div className="card">
                <div className="card-head">
                  <h3>Produtos ({prodsFiltrados.length})</h3>
                  <button className="btn btn-primary btn-sm" onClick={() => setModal({ tipo: 'produto', dados: null })}>+ Adicionar</button>
                </div>
                <div className="search-row"><input value={buscaProd} onChange={(e) => setBuscaProd(e.target.value)} placeholder="Buscar produto..." /></div>
                <div style={{ overflowX: 'auto' }}>
                  <table className="tbl"><thead><tr><th></th><th>Nome</th><th>Preço</th><th>Tamanhos</th><th>Estoque</th><th></th></tr></thead>
                    <tbody>{prodsFiltrados.map((p) => (
                      <tr key={p.id}>
                        <td>{p.imagem ? <img className="tbl-img" src={p.imagem} alt="" /> : '🐊'}</td>
                        <td><b>{p.nome}</b></td>
                        <td>{p.preco_promocional ? <>{api.formatarMoeda(p.preco_promocional)} <s style={{ color: 'var(--cinza-400)', fontSize: '.75rem' }}>{api.formatarMoeda(p.preco)}</s></> : api.formatarMoeda(p.preco)}</td>
                        <td>{p.tamanhos?.map((t) => t.tamanho).join(', ') || p.tamanho || '—'}</td>
                        <td>{p.stock}</td>
                        <td><div className="row-actions">
                          <button className="mini-btn" onClick={() => setModal({ tipo: 'produto', dados: p })}>Editar</button>
                          <button className="mini-btn danger" onClick={async () => { if (confirm('Deletar produto?')) { try { await api.deleteProduto(p.id); toast('Produto deletado.', 'success'); carregar('produtos'); } catch (e) { toast(e.message, 'error'); } } }}>Excluir</button>
                        </div></td>
                      </tr>
                    ))}</tbody></table>
                </div>
              </div>
            )}

            {tab === 'pedidos' && (
              <div className="card">
                <div className="card-head"><h3>Pedidos ({pedidosFiltrados.length}) — entrega 100% gerenciável: rastreio, transportadora e status</h3></div>
                <div className="tabs">{PED_ABAS.map(([v, l]) => <button key={v} className={`tab${aba === v ? ' active' : ''}`} onClick={() => setAba(v)}>{l}</button>)}</div>
                <div className="search-row"><input value={busca} onChange={(e) => setBusca(e.target.value)} placeholder="Buscar por nº do pedido ou cliente..." /></div>
                <TabelaPedidos lista={pedidosFiltrados} onEdit={(p) => setModal({ tipo: 'pedido', dados: p })}
                  onDelete={async (p) => { if (confirm('Deletar pedido?')) { try { await api.deletePedido(p.id_pedido || p.id); toast('Pedido deletado.', 'success'); carregar('pedidos'); } catch (e) { toast(e.message, 'error'); } } }} />
              </div>
            )}

            {tab === 'usuarios' && (
              <div className="card"><div className="card-head"><h3>Usuários ({usuarios.length})</h3></div>
                <div style={{ overflowX: 'auto' }}><table className="tbl"><thead><tr><th>ID</th><th>Username</th><th>Acesso</th></tr></thead>
                  <tbody>{usuarios.map((u) => <tr key={u.id}><td>{u.id}</td><td>{u.username}</td><td>{u.acesso}</td></tr>)}</tbody></table></div>
              </div>
            )}
            {tab === 'clientes' && (
              <div className="card"><div className="card-head"><h3>Clientes ({clientes.length})</h3></div>
                <div style={{ overflowX: 'auto' }}><table className="tbl"><thead><tr><th>ID</th><th>Nome</th><th>Email</th><th>Telefone</th><th>CPF</th></tr></thead>
                  <tbody>{clientes.map((c) => <tr key={c.id}><td>{c.id}</td><td>{c.nome}</td><td>{c.email}</td><td>{c.telefone}</td><td>{c.cpf || '—'}</td></tr>)}</tbody></table></div>
              </div>
            )}
            {tab === 'admins' && (
              <div className="card"><div className="card-head"><h3>Admins ({admins.length})</h3></div>
                <div style={{ overflowX: 'auto' }}><table className="tbl"><thead><tr><th>ID</th><th>Username</th></tr></thead>
                  <tbody>{admins.map((a) => <tr key={a.id}><td>{a.id}</td><td>{a.username}</td></tr>)}</tbody></table></div>
              </div>
            )}
          </>
        )}
      </div>

      {modal?.tipo === 'pedido' && <PedidoModal pedido={modal.dados} onClose={() => setModal(null)} onSave={salvarPedido} />}
      {modal?.tipo === 'produto' && <ProdutoModal produto={modal.dados} onClose={() => setModal(null)} onSave={salvarProduto} />}
    </div>
  );
}

function NotifyBar({ notify, trabalhando, onAlternar, autoReload, restante, onToggleReload }) {
  const ligado = notify.preferencia !== '0';
  const detalhe = !notify.suportado
    ? 'navegador sem suporte — avisos só no painel'
    : notify.permissao === 'denied'
      ? 'bloqueado no navegador — ative nas configurações do site'
      : notify.inscrito
        ? 'aparelho inscrito — avisa com site fechado'
        : 'avisa no painel + som; ative p/ receber com site fechado';
  return (
    <div className="notify-bar">
      <span className="notify-status" title={detalhe}>
        <span className={`notify-dot${ligado ? ' on' : ''}`} />
        🔔 Aparelho {ligado ? 'ativado' : 'pausado'}
        <small>{detalhe}</small>
      </span>
      <span className="notify-actions">
        <span className="notify-reload" title="Recarrega os dados da aba atual automaticamente">
          {autoReload ? `↻ em ${restante}s` : '↻ pausado'}
        </span>
        <button className="mini-btn" onClick={onToggleReload}>
          {autoReload ? 'Pausar reload' : 'Retomar reload'}
        </button>
        <button className="mini-btn" disabled={trabalhando} onClick={onAlternar}>
          {trabalhando ? '...' : ligado ? 'Pausar aparelho' : 'Ativar aparelho'}
        </button>
      </span>
    </div>
  );
}

function TabelaPedidos({ lista, onEdit, onDelete }) {
  if (!lista.length) return <p style={{ padding: 18, color: 'var(--cinza-500)' }}>Nenhum pedido encontrado.</p>;
  return (
    <div style={{ overflowX: 'auto' }}>
      <table className="tbl"><thead><tr><th>Pedido</th><th>Cliente</th><th>Status</th><th>Entrega</th><th>Rastreio</th><th>Total</th><th></th></tr></thead>
        <tbody>{lista.map((p) => (
          <tr key={p.id}>
            <td><b>{p.id_pedido || `#${p.id}`}</b></td>
            <td>{p.cliente_id}</td>
            <td>{p.status}</td>
            <td style={{ fontSize: '.78rem' }}>{p.entrega_tipo || '—'}</td>
            <td style={{ fontSize: '.78rem' }}>{p.codigo_rastreio ? <code>{p.codigo_rastreio}</code> : <span style={{ color: 'var(--cinza-400)' }}>—</span>}</td>
            <td>{api.formatarMoeda(p.valor_total)}</td>
            <td><div className="row-actions">
              <button className="mini-btn" onClick={() => onEdit(p)}>Gerenciar entrega</button>
              {onDelete && <button className="mini-btn danger" onClick={() => onDelete(p)}>Excluir</button>}
            </div></td>
          </tr>
        ))}</tbody></table>
    </div>
  );
}

function PedidoModal({ pedido, onClose, onSave }) {
  const [status, setStatus] = useState(pedido.status);
  const [rastreio, setRastreio] = useState(pedido.codigo_rastreio || '');
  const [transportadora, setTransportadora] = useState(pedido.transportadora || 'Correios');
  const isLocal = pedido.entrega_tipo?.includes('Retirada') || pedido.entrega_tipo?.includes('Uber');

  return (
    <div className="modal-overlay show" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()} style={{ textAlign: 'left' }}>
        <div className="drawer-head"><h2>Pedido {pedido.id_pedido || `#${pedido.id}`}</h2><button className="icon-btn" onClick={onClose}>✕</button></div>
        <div className="drawer-body">
          <p style={{ fontSize: '.86rem', color: 'var(--cinza-500)' }}>Cliente #{pedido.cliente_id} • {api.formatarMoeda(pedido.valor_total)} • {pedido.entrega_tipo}</p>
          <p style={{ fontSize: '.85rem', margin: '8px 0 14px' }}>{pedido.endereco_entrega}</p>
          <div className="form-group"><label className="form-label">Status</label>
            <select value={status} onChange={(e) => setStatus(e.target.value)}>
              <option value="pendente">Pendente</option>
              <option value="Pago">Pago</option>
              <option value="Enviado">Enviado</option>
              <option value="Entregue">Entregue</option>
              <option value="Recusado">Recusado</option>
            </select>
          </div>
          {isLocal ? (
            <div className="notice notice-info">Entrega local ({pedido.entrega_tipo}) — combine pelo WhatsApp com o cliente. Rastreio dos Correios não se aplica.</div>
          ) : (
            <>
              <div className="form-group"><label className="form-label">Código de Rastreio (Correios) *</label>
                <input value={rastreio} onChange={(e) => setRastreio(e.target.value.toUpperCase())} placeholder="Ex: AB123456789CD" style={{ fontFamily: 'monospace' }} />
                <p className="form-hint">Ao salvar com código, o pedido vira “Enviado” e o cliente é notificado (email + WhatsApp).</p>
              </div>
              <div className="form-group"><label className="form-label">Transportadora</label>
                <select value={transportadora} onChange={(e) => setTransportadora(e.target.value)}>
                  <option>Correios</option><option>Jadlog</option><option>Outra</option>
                </select>
              </div>
            </>
          )}
        </div>
        <div className="drawer-foot" style={{ display: 'flex', gap: 8 }}>
          <button className="btn btn-ghost" onClick={onClose} style={{ flex: 1 }}>Cancelar</button>
          <button className="btn btn-primary" style={{ flex: 2 }}
            onClick={() => onSave(pedido.id_pedido || pedido.id, isLocal ? { status } : { status, codigo_rastreio: rastreio.trim() || null, transportadora })}>
            Salvar entrega
          </button>
        </div>
      </div>
    </div>
  );
}

function ProdutoModal({ produto, onClose, onSave }) {
  const [nome, setNome] = useState(produto?.nome || '');
  const [preco, setPreco] = useState(produto?.preco ?? '');
  const [promo, setPromo] = useState(produto?.preco_promocional ?? '');
  const [tams, setTams] = useState(
    produto?.tamanhos?.length ? produto.tamanhos.map((t) => ({ tamanho: t.tamanho, stock: t.stock })) : [{ tamanho: 'M', stock: 10 }],
  );
  const [imagemUrl, setImagemUrl] = useState(produto?.imagem || '');
  const [file, setFile] = useState(null);
  const [saving, setSaving] = useState(false);
  const { toast } = useToast();

  const salvar = async () => {
    if (!nome.trim() || !preco) return toast('Preencha nome e preço.', 'error');
    if (!tams.length || tams.some((t) => !t.tamanho)) return toast('Informe ao menos um tamanho.', 'error');
    setSaving(true);
    try {
      let imagem = imagemUrl;
      if (file) {
        const r = await api.uploadImagem(file);
        imagem = r.url;
      }
      await onSave(produto?.id, {
        nome: nome.trim(), preco: Number(preco),
        preco_promocional: promo === '' ? null : Number(promo),
        imagem, imagens: imagem ? [imagem] : [],
        tamanhos: tams.map((t) => ({ tamanho: t.tamanho, stock: Number(t.stock) || 0 })),
      });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="modal-overlay show" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()} style={{ textAlign: 'left' }}>
        <div className="drawer-head"><h2>{produto ? 'Editar Produto' : 'Novo Produto'}</h2><button className="icon-btn" onClick={onClose}>✕</button></div>
        <div className="drawer-body">
          <div className="form-group"><label className="form-label">Nome *</label><input value={nome} onChange={(e) => setNome(e.target.value)} /></div>
          <div className="form-row">
            <div className="form-group"><label className="form-label">Preço *</label><input type="number" step="0.01" value={preco} onChange={(e) => setPreco(e.target.value)} /></div>
            <div className="form-group"><label className="form-label">Promo (opcional)</label><input type="number" step="0.01" value={promo} onChange={(e) => setPromo(e.target.value)} /></div>
          </div>
          <div className="form-group"><label className="form-label">Tamanhos e estoque *</label>
            {tams.map((t, i) => (
              <div className="tam-row" key={i}>
                <select value={t.tamanho} onChange={(e) => setTams(tams.map((x, j) => j === i ? { ...x, tamanho: e.target.value } : x))}>
                  {['P', 'M', 'G', 'GG', 'XG'].map((s) => <option key={s}>{s}</option>)}
                </select>
                <input type="number" min={0} value={t.stock} onChange={(e) => setTams(tams.map((x, j) => j === i ? { ...x, stock: e.target.value } : x))} placeholder="Estoque" />
                <button className="mini-btn danger" onClick={() => setTams(tams.filter((_, j) => j !== i))}>✕</button>
              </div>
            ))}
            <button className="mini-btn" onClick={() => setTams([...tams, { tamanho: 'M', stock: 10 }])}>+ Tamanho</button>
          </div>
          <div className="form-group"><label className="form-label">Imagem (URL ou arquivo)</label>
            <input value={imagemUrl} onChange={(e) => setImagemUrl(e.target.value)} placeholder="https://..." />
            <input type="file" accept="image/jpeg,image/png,image/webp" style={{ marginTop: 8 }} onChange={(e) => setFile(e.target.files?.[0] || null)} />
            {(imagemUrl || produto?.imagem) && <img src={imagemUrl || produto.imagem} alt="" style={{ width: 90, height: 90, objectFit: 'cover', borderRadius: 10, marginTop: 8 }} />}
          </div>
        </div>
        <div className="drawer-foot" style={{ display: 'flex', gap: 8 }}>
          <button className="btn btn-ghost" onClick={onClose} style={{ flex: 1 }}>Cancelar</button>
          <button className="btn btn-primary" style={{ flex: 2 }} disabled={saving} onClick={salvar}>{saving ? 'Salvando...' : produto ? 'Salvar' : 'Criar'}</button>
        </div>
      </div>
    </div>
  );
}
