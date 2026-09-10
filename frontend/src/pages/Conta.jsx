import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import { useAuth } from '../store/AuthContext';
import { useToast } from '../store/ToastContext';

function maskFone(v) {
  let d = v.replace(/\D/g, '').slice(0, 11);
  if (d.length > 6) return `(${d.slice(0, 2)}) ${d.slice(2, 7)}-${d.slice(7)}`;
  if (d.length > 2) return `(${d.slice(0, 2)}) ${d.slice(2)}`;
  if (d.length > 0) return `(${d}`;
  return d;
}
function maskCpf(v) {
  let d = v.replace(/\D/g, '').slice(0, 11);
  return d.replace(/(\d{3})(\d)/, '$1.$2').replace(/(\d{3})(\d)/, '$1.$2').replace(/(\d{3})(\d{1,2})$/, '$1-$2');
}

export default function Conta() {
  const { user, logout } = useAuth();
  const { toast } = useToast();
  const navigate = useNavigate();
  const [clienteId, setClienteId] = useState(null);
  const [original, setOriginal] = useState({});
  const [form, setForm] = useState({ nome: '', email: '', telefone: '', cpf: '' });
  const [saving, setSaving] = useState(false);
  const [ok, setOk] = useState(false);

  useEffect(() => {
    if (!user) { navigate('/login', { replace: true }); return; }
    (async () => {
      try {
        const data = await api.getClientes({ email: user.username });
        const c = data.clientes?.[0];
        if (c) {
          setClienteId(c.id);
          setOriginal({ ...c });
          setForm({ nome: c.nome || '', email: c.email || '', telefone: c.telefone || '', cpf: c.cpf || '' });
        } else {
          setForm((f) => ({ ...f, email: user.username }));
        }
      } catch { /* ignore */ }
    })();
  }, [user, navigate]);

  const salvar = async (e) => {
    e.preventDefault();
    if (!form.nome.trim() || !form.email.trim()) return toast('Preencha Nome e Email.', 'error');
    setSaving(true);
    try {
      if (clienteId) {
        const payload = {};
        if (form.nome !== original.nome) payload.nome = form.nome.trim();
        if (form.email !== original.email) payload.email = form.email.trim();
        if (form.telefone !== original.telefone) payload.telefone = form.telefone.trim();
        if (form.cpf !== original.cpf) payload.cpf = form.cpf.trim();
        if (Object.keys(payload).length) {
          await api.updateCliente(clienteId, payload);
          setOriginal({ ...original, ...payload });
        }
      } else {
        const novo = await api.createCliente({ nome: form.nome.trim(), email: form.email.trim(), telefone: form.telefone.trim(), cpf: form.cpf.trim() });
        setClienteId(novo.id);
        setOriginal({ ...novo });
      }
      try {
        if (user?.username) sessionStorage.setItem(`cliente_vinculado_${user.username}`, JSON.stringify({ id: clienteId, email: form.email, nome: form.nome }));
      } catch { /* ignore */ }
      setOk(true);
      setTimeout(() => setOk(false), 3000);
      toast('Dados atualizados com sucesso!', 'success');
    } catch (err) {
      toast(err.message, 'error');
    } finally {
      setSaving(false);
    }
  };

  const resetSenha = async () => {
    if (!original.email && !form.email) return toast('Cadastre seu email primeiro.', 'error');
    try {
      await api.esqueciSenha(original.email || form.email);
      toast('Link de redefinição enviado para seu email!', 'success');
    } catch (e) {
      toast(e.message, 'error');
    }
  };

  return (
    <main>
      <div className="page-hero"><div className="container">
        <span className="eyebrow">Meu Perfil</span>
        <h1>Minha Conta</h1>
        <p>Gerencie seus dados — eles são usados para agilizar suas compras e a entrega.</p>
      </div></div>
      <div className="container">
        <div className="account-grid">
          <aside className="account-side" style={{ textAlign: 'center' }}>
            <div className="avatar" style={{ margin: '0 auto 10px' }}>{(form.nome || user?.username || '?').charAt(0).toUpperCase()}</div>
            <h2 style={{ fontSize: '1.1rem' }}>{form.nome || user?.username}</h2>
            <p style={{ color: 'var(--cinza-500)', fontSize: '.85rem' }}>{form.email || '-'}</p>
            <button className="btn btn-outline btn-sm btn-block" style={{ marginTop: 14 }} onClick={() => { logout(); navigate('/login'); }}>Sair da Conta</button>
          </aside>
          <div className="account-main">
            <h3 style={{ fontFamily: 'var(--font-serif)', marginBottom: 4 }}>Dados Pessoais</h3>
            <p style={{ color: 'var(--cinza-500)', fontSize: '.86rem', marginBottom: 16 }}>Obrigatórios para finalizar compras (nome, email, telefone e CPF).</p>
            <form onSubmit={salvar}>
              <div className="form-row">
                <div className="form-group"><label className="form-label">Nome Completo *</label><input value={form.nome} onChange={(e) => setForm({ ...form, nome: e.target.value })} placeholder="Seu nome" /></div>
                <div className="form-group"><label className="form-label">Email *</label><input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} placeholder="seu@email.com" /></div>
              </div>
              <div className="form-row">
                <div className="form-group"><label className="form-label">Telefone *</label><input value={form.telefone} onChange={(e) => setForm({ ...form, telefone: maskFone(e.target.value) })} placeholder="(11) 99999-9999" /></div>
                <div className="form-group"><label className="form-label">CPF *</label><input value={form.cpf} onChange={(e) => setForm({ ...form, cpf: maskCpf(e.target.value) })} placeholder="000.000.000-00" /></div>
              </div>
              <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
                <button className="btn btn-primary" disabled={saving}>{saving ? 'Salvando...' : 'Salvar Alterações'}</button>
                <button type="button" className="btn btn-ghost" onClick={() => setForm({ nome: original.nome || '', email: original.email || '', telefone: original.telefone || '', cpf: original.cpf || '' })}>Cancelar</button>
              </div>
              {ok && <div className="notice notice-ok" style={{ marginTop: 12 }}>✅ Dados atualizados com sucesso!</div>}
            </form>
            <hr style={{ border: 'none', borderTop: '1px solid var(--cinza-200)', margin: '22px 0' }} />
            <h3 style={{ fontFamily: 'var(--font-serif)', marginBottom: 4 }}>Segurança</h3>
            <p style={{ color: 'var(--cinza-500)', fontSize: '.86rem', marginBottom: 12 }}>Altere sua senha de acesso por email.</p>
            <button className="btn btn-outline btn-sm" onClick={resetSenha}>Alterar Senha</button>
          </div>
        </div>
      </div>
    </main>
  );
}
