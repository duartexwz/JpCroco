import { useState } from 'react';
import { Link, useSearchParams, useNavigate } from 'react-router-dom';
import { api } from '../api/client';

export default function RedefinirSenha() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const token = params.get('token') || '';
  const [senha, setSenha] = useState('');
  const [confirma, setConfirma] = useState('');
  const [erro, setErro] = useState('');
  const [ok, setOk] = useState(false);
  const [loading, setLoading] = useState(false);

  const enviar = async (e) => {
    e.preventDefault();
    setErro('');
    if (!token) return setErro('Link inválido ou expirado.');
    if (senha.length < 6) return setErro('A senha deve ter no mínimo 6 caracteres.');
    if (senha !== confirma) return setErro('As senhas não conferem.');
    setLoading(true);
    try {
      await api.redefinirSenha(token, senha);
      setOk(true);
      setTimeout(() => navigate('/login'), 2500);
    } catch (err) {
      setErro(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-wrap">
      <div className="auth-hero">
        <span className="eyebrow">🔒 Segurança</span>
        <h1>Redefina sua senha.</h1>
        <p>Escolha uma senha forte para proteger sua conta.</p>
      </div>
      <div className="auth-form-side">
        <div className="auth-card">
          <h1 style={{ fontFamily: 'var(--font-serif)' }}>Nova senha</h1>
          {erro && <div className="auth-error show" style={{ marginTop: 12 }}>{erro}</div>}
          {ok ? (
            <div style={{ textAlign: 'center', marginTop: 16 }}>
              <div style={{ fontSize: '2.4rem' }}>✅</div>
              <p>Senha redefinida! Redirecionando para o login...</p>
            </div>
          ) : (
            <form onSubmit={enviar} style={{ marginTop: 16 }}>
              <div className="form-group"><label className="form-label">Nova senha</label><input type="password" required value={senha} onChange={(e) => setSenha(e.target.value)} /></div>
              <div className="form-group"><label className="form-label">Confirmar senha</label><input type="password" required value={confirma} onChange={(e) => setConfirma(e.target.value)} /></div>
              <button className="btn btn-primary btn-block" disabled={loading}>{loading ? 'Salvando...' : 'Redefinir Senha'}</button>
            </form>
          )}
          <div style={{ textAlign: 'center', marginTop: 14 }}><Link to="/login" style={{ fontSize: '.85rem', color: 'var(--cinza-500)' }}>← Voltar ao login</Link></div>
        </div>
      </div>
    </div>
  );
}
