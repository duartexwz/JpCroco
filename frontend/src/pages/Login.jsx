import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import { useAuth } from '../store/AuthContext';

export default function Login() {
  const { login, user } = useAuth();
  const navigate = useNavigate();
  const [modo, setModo] = useState('login'); // login | register | forgot
  const [erro, setErro] = useState('');
  const [ok, setOk] = useState(false);
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState({ email: '', senha: '', nome: '', confirma: '' });

  if (user) {
    navigate(user.acesso === 'admin' ? '/admin' : '/', { replace: true });
    return null;
  }

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const entrar = async (e) => {
    e.preventDefault();
    setErro('');
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) return setErro('Informe um email válido.');
    setLoading(true);
    try {
      await login(form.email.trim(), form.senha);
      navigate('/', { replace: true });
    } catch (err) {
      setErro(err.message);
    } finally {
      setLoading(false);
    }
  };

  const registrar = async (e) => {
    e.preventDefault();
    setErro('');
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) return setErro('Informe um email válido.');
    if (!form.nome.trim()) return setErro('Informe seu nome completo.');
    if (form.senha !== form.confirma) return setErro('As senhas não conferem.');
    if (form.senha.length < 6) return setErro('A senha deve ter no mínimo 6 caracteres.');
    setLoading(true);
    try {
      await api.createUsuario({ username: form.email.trim(), password: form.senha, acesso: 'comum', nome_completo: form.nome.trim() });
      await login(form.email.trim(), form.senha);
      navigate('/conta', { replace: true });
    } catch (err) {
      setErro(err.message);
    } finally {
      setLoading(false);
    }
  };

  const esqueci = async (e) => {
    e.preventDefault();
    setErro('');
    setLoading(true);
    try {
      await api.esqueciSenha(form.email.trim());
      setOk(true);
    } catch (err) {
      setErro(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-wrap">
      <div className="auth-hero">
        <span className="eyebrow">🐊 JP Croco</span>
        <h1>Elegância que nasce da confiança.</h1>
        <p>Entre para comprar com pagamento seguro, rastreio em tempo real e entrega para todo o Brasil.</p>
      </div>
      <div className="auth-form-side">
        <div className="auth-card">
          <h1 style={{ fontFamily: 'var(--font-serif)', fontSize: '1.6rem' }}>
            {modo === 'login' ? 'Bem-vindo de volta' : modo === 'register' ? 'Criar Conta' : 'Recuperar senha'}
          </h1>
          <p style={{ color: 'var(--cinza-500)', fontSize: '.9rem', margin: '4px 0 18px' }}>
            {modo === 'login' ? 'Entre com sua conta para continuar' : modo === 'register' ? 'Preencha seus dados para se cadastrar' : 'Enviaremos um link para seu email'}
          </p>
          {erro && <div className="auth-error show">{erro}</div>}

          {modo === 'login' && (
            <form onSubmit={entrar}>
              <div className="form-group"><label className="form-label">Email</label><input type="email" required value={form.email} onChange={set('email')} placeholder="seu@email.com" /></div>
              <div className="form-group"><label className="form-label">Senha</label><input type="password" required value={form.senha} onChange={set('senha')} placeholder="Sua senha" /></div>
              <div style={{ textAlign: 'right', marginBottom: 12 }}>
                <button type="button" onClick={() => { setModo('forgot'); setErro(''); }} style={{ color: 'var(--verde)', fontWeight: 600, fontSize: '.85rem' }}>Esqueci minha senha</button>
              </div>
              <button className="btn btn-primary btn-block btn-lg" disabled={loading}>{loading ? 'Entrando...' : 'Entrar'}</button>
            </form>
          )}

          {modo === 'register' && (
            <form onSubmit={registrar}>
              <div className="form-group"><label className="form-label">Email</label><input type="email" required value={form.email} onChange={set('email')} placeholder="seu@email.com" /></div>
              <div className="form-group"><label className="form-label">Nome Completo</label><input required value={form.nome} onChange={set('nome')} placeholder="Seu nome completo" /></div>
              <div className="form-row">
                <div className="form-group"><label className="form-label">Senha</label><input type="password" required minLength={6} value={form.senha} onChange={set('senha')} placeholder="Mín. 6 caracteres" /></div>
                <div className="form-group"><label className="form-label">Confirmar</label><input type="password" required value={form.confirma} onChange={set('confirma')} placeholder="Repita a senha" /></div>
              </div>
              <button className="btn btn-primary btn-block btn-lg" disabled={loading}>{loading ? 'Criando...' : 'Criar Conta'}</button>
            </form>
          )}

          {modo === 'forgot' && !ok && (
            <form onSubmit={esqueci}>
              <div className="form-group"><label className="form-label">Email cadastrado</label><input type="email" required value={form.email} onChange={set('email')} placeholder="seu@email.com" /></div>
              <button className="btn btn-primary btn-block" disabled={loading}>{loading ? 'Enviando...' : 'Enviar Link'}</button>
              <button type="button" className="btn btn-ghost btn-block" onClick={() => setModo('login')}>Voltar ao Login</button>
            </form>
          )}
          {modo === 'forgot' && ok && (
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '2.4rem' }}>📩</div>
              <h3>Email enviado!</h3>
              <p style={{ color: 'var(--cinza-500)', fontSize: '.9rem', margin: '6px 0 16px' }}>Verifique sua caixa de entrada e clique no link.</p>
              <button className="btn btn-primary btn-block" onClick={() => { setModo('login'); setOk(false); }}>Voltar ao Login</button>
            </div>
          )}

          {modo !== 'forgot' && (
            <div className="auth-toggle">
              {modo === 'login' ? 'Não tem conta?' : 'Já tem conta?'}
              <button onClick={() => { setModo(modo === 'login' ? 'register' : 'login'); setErro(''); }}>
                {modo === 'login' ? 'Cadastre-se' : 'Entrar'}
              </button>
            </div>
          )}
          <div style={{ textAlign: 'center', marginTop: 14 }}>
            <Link to="/" style={{ fontSize: '.85rem', color: 'var(--cinza-500)' }}>← Voltar para a loja</Link>
          </div>
        </div>
      </div>
    </div>
  );
}
