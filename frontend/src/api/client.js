// Cliente HTTP espelhando o antigo script/api.js — pagamento intacto.
const API_BASE = (import.meta.env.VITE_API_URL || '/api').replace(/\/$/, '');

function getToken() {
  return sessionStorage.getItem('access_token') || localStorage.getItem('access_token');
}
function getUser() {
  const raw = sessionStorage.getItem('user') || localStorage.getItem('user');
  if (!raw) return null;
  try {
    const user = JSON.parse(raw);
    const token = getToken();
    if (token) {
      try {
        const payload = JSON.parse(atob(token.split('.')[1]));
        if (payload.acesso && user.acesso !== payload.acesso) {
          user.acesso = payload.acesso;
          sessionStorage.setItem('user', JSON.stringify(user));
        }
      } catch { /* ignore */ }
    }
    return user;
  } catch {
    return null;
  }
}

async function request(path, options = {}) {
  // Normaliza: chama /api/payments/... como /payments/... (vite proxy já tem /api)
  const clean = path.startsWith('/api/') ? path.slice(4) : path;
  const url = `${API_BASE}${clean}`;
  const doFetch = async (token) => {
    const headers = { ...(options.headers || {}) };
    if (token) headers.Authorization = `Bearer ${token}`;
    if (options.body && !(options.body instanceof FormData) && !headers['Content-Type']) {
      headers['Content-Type'] = 'application/json';
    }
    try {
      return await fetch(url, { ...options, headers });
    } catch {
      throw new Error('Erro de conexão com o servidor.');
    }
  };
  let res = await doFetch(getToken());
  // 401 em rota autenticada: tenta renovar o token em silêncio UMA vez e
  // repete a requisição. Só desloga se a renovação falhar.
  if (res.status === 401 && !path.includes('/login')) {
    try {
      await refreshToken();
      res = await doFetch(getToken());
    } catch {
      logoutLocal();
      window.location.href = '/#/login';
      throw new Error('Sessão expirada. Faça login novamente.');
    }
  }
  let data = null;
  try {
    data = await res.json();
  } catch {
    data = null;
  }
  if (!res.ok) {
    const msg = data?.detail?.[0]?.msg || data?.message || data?.detail || 'Erro na requisição';
    throw new Error(typeof msg === 'string' ? msg : 'Erro na requisição');
  }
  return data;
}

// Renovação compartilhada: requisições 401 simultâneas usam a mesma promise.
let refreshing = null;
async function refreshToken() {
  if (!refreshing) {
    refreshing = (async () => {
      const old = getToken();
      if (!old) throw new Error('sem token');
      const res = await fetch(`${API_BASE}/login/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: old }),
      });
      if (!res.ok) throw new Error('refresh negado');
      const data = await res.json();
      if (!data?.access_token) throw new Error('refresh sem token');
      sessionStorage.setItem('access_token', data.access_token);
      return data.access_token;
    })().finally(() => { refreshing = null; });
  }
  return refreshing;
}

function logoutLocal() {
  sessionStorage.removeItem('access_token');
  sessionStorage.removeItem('user');
  localStorage.removeItem('access_token');
  localStorage.removeItem('user');
}

function buildQuery(params = {}) {
  const entries = Object.entries(params).filter(([, v]) => v !== null && v !== undefined && v !== '');
  if (!entries.length) return '';
  return `?${new URLSearchParams(entries).toString()}`;
}

export const api = {
  getToken,
  getUser,
  isLoggedIn: () => !!getToken(),
  request,
  buildQuery,
  formatarMoeda: (v) =>
    new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(Number(v) || 0),

  login: async (username, password) => {
    const data = await request('/login/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({ username, password }),
    });
    sessionStorage.setItem('access_token', data.access_token);
    localStorage.removeItem('access_token');
    let acesso = 'comum';
    try {
      acesso = JSON.parse(atob(data.access_token.split('.')[1])).acesso || 'comum';
    } catch { /* ignore */ }
    // admin pode logar como admin ou comum; normaliza 'usuario' -> 'comum'
    if (acesso === 'usuario') acesso = 'comum';
    sessionStorage.setItem('user', JSON.stringify({ username, acesso }));
    localStorage.removeItem('user');
    return data;
  },
  logout: () => {
    sessionStorage.clear();
    localStorage.removeItem('access_token');
    localStorage.removeItem('user');
    localStorage.removeItem('carrinho');
  },

  createUsuario: (d) => request('/usuarios/', { method: 'POST', body: JSON.stringify(d) }),
  getUsuarios: (p = {}) => request(`/usuarios/${buildQuery(p)}`),
  esqueciSenha: (email) => request('/login/esqueci-senha', { method: 'POST', body: JSON.stringify({ email }) }),
  redefinirSenha: (token, nova_senha) =>
    request('/login/redefinir-senha', { method: 'POST', body: JSON.stringify({ token, nova_senha }) }),

  getProdutos: (p = {}) => request(`/produtos/${buildQuery(p)}`),
  createProduto: (d) => request('/produtos/', { method: 'POST', body: JSON.stringify(d) }),
  updateProduto: (id, d) => request(`/produtos/${id}`, { method: 'PATCH', body: JSON.stringify(d) }),
  deleteProduto: (id) => request(`/produtos/${id}`, { method: 'DELETE' }),

  getClientes: (p = {}) => request(`/clientes/${buildQuery(p)}`),
  getClienteByEmail: async (email) => {
    const data = await request(`/clientes/${buildQuery({ email })}`).catch(() => null);
    return data?.clientes?.[0] || null;
  },
  createCliente: (d) => request('/clientes/', { method: 'POST', body: JSON.stringify(d) }),
  updateCliente: (id, d) => request(`/clientes/${id}`, { method: 'PATCH', body: JSON.stringify(d) }),
  deleteCliente: (id) => request(`/clientes/${id}`, { method: 'DELETE' }),

  createPedido: (d) => request('/pedidos/', { method: 'POST', body: JSON.stringify(d) }),
  getPedidos: (p = {}) => request(`/pedidos/${buildQuery(p)}`),
  getMeusPedidos: () => request('/pedidos/meus'),
  updatePedido: (id, d) => request(`/pedidos/${id}`, { method: 'PATCH', body: JSON.stringify(d) }),
  deletePedido: (id) => request(`/pedidos/${id}`, { method: 'DELETE' }),

  createItemPedido: (d) => request('/itens_pedido/', { method: 'POST', body: JSON.stringify(d) }),
  getItensPedido: (p = {}) => request(`/itens_pedido/${buildQuery(p)}`),

  // ---- Entrega (100% funcional) ----
  calcularFrete: (d) => request('/frete/calcular', { method: 'POST', body: JSON.stringify(d) }),
  consultarCep: async (cep) => {
    const numeros = String(cep).replace(/\D/g, '');
    return request(`/endereco/cep/${numeros}`);
  },
  rastrear: (codigo) => request(`/rastreio/${encodeURIComponent(String(codigo).trim().toUpperCase())}`),

  // ---- Pagamento (Brick -> /payments/process; o nginx remove o /api no proxy) ----
  getPublicKey: () => request('/webhook/public-key').catch(() => request('/payments/public-key')),
  processPayment: (pedido_id, formData, idempotencyKey) =>
    request('/payments/process', {
      method: 'POST',
      headers: { 'X-Idempotency-Key': idempotencyKey },
      body: JSON.stringify({ pedido_id, formData }),
    }),
  getPaymentStatus: (paymentId) => request(`/payments/status/${paymentId}`),

  // Admin
  getAdmins: (p = {}) => request(`/admins/${buildQuery(p)}`),
  createAdmin: (d) => request('/admins/', { method: 'POST', body: JSON.stringify(d) }),
  updateAdmin: (id, d) => request(`/admins/${id}`, { method: 'PATCH', body: JSON.stringify(d) }),
  deleteAdmin: (id) => request(`/admins/${id}`, { method: 'DELETE' }),

  uploadImagem: async (file) => {
    const fd = new FormData();
    fd.append('file', file);
    return request('/upload/imagem', { method: 'POST', body: fd });
  },
  uploadImagens: async (files) => {
    const fd = new FormData();
    [...files].forEach((f) => fd.append('files', f));
    return request('/upload/imagem', { method: 'POST', body: fd });
  },
};

export const VENDEDOR_WHATSAPP =
  import.meta.env.VITE_VENDEDOR_WHATSAPP || '5561996803932';

// Protocolo público do pedido. O #id interno do banco NUNCA é exibido ao
// cliente — quando ainda não há protocolo, retorna null e a UI mostra um
// texto neutro ("Pedido em processamento").
export const protocoloPedido = (p) => p?.id_pedido || p?.protocolo || null;
