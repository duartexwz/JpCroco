import { createContext, useCallback, useContext, useMemo, useState } from 'react';

const ToastCtx = createContext(null);
let seq = 0;

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);

  const push = useCallback((mensagem, tipo = 'info') => {
    const id = ++seq;
    setToasts((t) => [...t, { id, mensagem, tipo }]);
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 3400);
  }, []);

  const value = useMemo(() => ({ toasts, toast: push }), [toasts, push]);
  return (
    <ToastCtx.Provider value={value}>
      {children}
      <div className="toasts">
        {toasts.map((t) => (
          <div key={t.id} className={`toast ${t.tipo}`}>{t.mensagem}</div>
        ))}
      </div>
    </ToastCtx.Provider>
  );
}

export const useToast = () => useContext(ToastCtx);
