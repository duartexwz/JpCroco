import { useCallback, useEffect, useRef, useState } from 'react';
import { api } from '../api/client';

const PREF_KEY = 'admin_notify'; // '1' = aparelho notifica | '0' = só painel

function b64ToU8(b64) {
  const pad = '='.repeat((4 - (b64.length % 4)) % 4);
  const s = (b64 + pad).replace(/-/g, '+').replace(/_/g, '/');
  const raw = atob(s);
  const out = new Uint8Array(raw.length);
  for (let i = 0; i < raw.length; i++) out[i] = raw.charCodeAt(i);
  return out;
}

function beep() {
  try {
    const Ctx = window.AudioContext || window.webkitAudioContext;
    if (!Ctx) return;
    const ctx = new Ctx();
    [0, 0.22].forEach((delay) => {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.frequency.value = 880;
      const t = ctx.currentTime + delay;
      gain.gain.setValueAtTime(0.001, t);
      gain.gain.exponentialRampToValueAtTime(0.25, t + 0.02);
      gain.gain.exponentialRampToValueAtTime(0.001, t + 0.18);
      osc.start(t);
      osc.stop(t + 0.2);
    });
    setTimeout(() => ctx.close().catch(() => {}), 800);
  } catch { /* sem áudio: segue silencioso */ }
}

/**
 * Notificação do aparelho do admin logado na sessão.
 * - Painel: quem chama decide o toast (já existe no Admin).
 * - Aparelho: Notification do sistema via Service Worker (funciona com o
 *   site fechado quando há push do backend) + som + vibração + título da aba.
 * A inscrição push é vinculada à sessão do admin (endpoint exige login admin).
 */
export function useAdminNotify() {
  const [permissao, setPermissao] = useState(() =>
    typeof Notification !== 'undefined' ? Notification.permission : 'indisponivel',
  );
  const [inscrito, setInscrito] = useState(false);
  const [preferencia, setPreferencia] = useState(() => {
    try {
      return localStorage.getItem(PREF_KEY) ?? '1';
    } catch {
      return '1';
    }
  });
  const regRef = useRef(null);
  const titleTimer = useRef(null);
  const titleOrig = useRef(document.title);
  const prefRef = useRef(preferencia);
  useEffect(() => { prefRef.current = preferencia; }, [preferencia]);

  const suportado =
    typeof window !== 'undefined' && 'Notification' in window && 'serviceWorker' in navigator && 'PushManager' in window;

  const registrarSW = useCallback(async () => {
    if (regRef.current) return regRef.current;
    regRef.current = await navigator.serviceWorker.register('/sw.js');
    return regRef.current;
  }, []);

  const inscreverPush = useCallback(async () => {
    // Chave VAPID pública vem do backend; sem ela, push com site fechado fica indisponível.
    const vap = await api.request('/push/vapid-key').catch(() => null);
    const key = vap?.public_key;
    if (!key) return false;
    const reg = await registrarSW();
    let sub = await reg.pushManager.getSubscription();
    if (!sub) {
      sub = await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: b64ToU8(key) });
    }
    await api.request('/push/subscribe', { method: 'POST', body: JSON.stringify(sub.toJSON()) });
    setInscrito(true);
    return true;
  }, [registrarSW]);

  const desinscreverPush = useCallback(async () => {
    try {
      const sub = await regRef.current?.pushManager.getSubscription();
      const endpoint = sub?.endpoint;
      if (sub) await sub.unsubscribe();
      if (endpoint) await api.request('/push/unsubscribe', { method: 'POST', body: JSON.stringify({ endpoint }) }).catch(() => {});
    } catch { /* ignore */ }
    setInscrito(false);
  }, []);

  const salvarPref = useCallback((v) => {
    setPreferencia(v);
    try {
      localStorage.setItem(PREF_KEY, v);
    } catch { /* ignore */ }
  }, []);

  const ativar = useCallback(async () => {
    salvarPref('1');
    if (!suportado) return 'painel';
    try {
      if (Notification.permission === 'default') {
        await Notification.requestPermission();
      }
      setPermissao(Notification.permission);
      if (Notification.permission !== 'granted') return 'bloqueado';
      await registrarSW();
      const ok = await inscreverPush().catch(() => false);
      return ok ? 'ok' : 'sem-push';
    } catch {
      return 'erro';
    }
  }, [suportado, registrarSW, inscreverPush, salvarPref]);

  const desativar = useCallback(async () => {
    salvarPref('0');
    await desinscreverPush();
    if (titleTimer.current) {
      clearInterval(titleTimer.current);
      titleTimer.current = null;
      document.title = titleOrig.current;
    }
  }, [desinscreverPush, salvarPref]);

  // Se a sessão já tinha permissão concedida, reinscreve o aparelho em silêncio.
  useEffect(() => {
    if (preferencia === '0' || !suportado) return;
    if (typeof Notification !== 'undefined' && Notification.permission === 'granted') {
      registrarSW().then(() => inscreverPush().catch(() => {})).catch(() => {});
    }
  }, [preferencia, suportado, registrarSW, inscreverPush]);

  useEffect(() => () => {
    if (titleTimer.current) clearInterval(titleTimer.current);
  }, []);

  /** Notifica o APARELHO (painel continua por conta do toast do chamador). */
  const notificarAparelho = useCallback(async (titulo, corpo) => {
      if (prefRef.current === '0') return;
      // 1) Sistema: via SW (tela bloqueada) ou Notification direta
      let sistemaOk = false;
      try {
        if (regRef.current && Notification.permission === 'granted') {
          await regRef.current.showNotification(titulo, {
            body: corpo, tag: 'jpcroco-pedido', renotify: true, vibrate: [200, 100, 200], data: { url: '/admin' },
          });
          sistemaOk = true;
        }
      } catch { /* cai no fallback */ }
      if (!sistemaOk) {
        try {
          if (Notification.permission === 'granted') {
            new Notification(titulo, { body: corpo });
            sistemaOk = true;
          }
        } catch { /* sem sistema: som + título cobrem */ }
      }
      // 2) Som + vibração no aparelho
      beep();
      try {
        if (navigator.vibrate) navigator.vibrate([200, 100, 200]);
      } catch { /* ignore */ }
      // 3) Pisca o título da aba
      try {
        if (!titleTimer.current) {
          titleOrig.current = document.title;
          let on = false;
          let vezes = 0;
          titleTimer.current = setInterval(() => {
            on = !on;
            vezes += 1;
            document.title = on ? `🔔 ${titulo}` : titleOrig.current;
            if ((!on && document.hasFocus()) || vezes > 20) {
              clearInterval(titleTimer.current);
              titleTimer.current = null;
              document.title = titleOrig.current;
            }
          }, 1000);
        }
      } catch { /* ignore */ }
    },
    [],
  );

  return { suportado, permissao, inscrito, preferencia, ativar, desativar, notificarAparelho };
}
