import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { api } from '../api/client';

const AuthCtx = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => api.getUser());
  const [ready, setReady] = useState(false);

  useEffect(() => {
    setUser(api.getUser());
    setReady(true);
  }, []);

  const login = useCallback(async (username, password) => {
    await api.login(username, password);
    setUser(api.getUser());
  }, []);

  const logout = useCallback(() => {
    api.logout();
    try {
      sessionStorage.removeItem('carrinho');
    } catch { /* ignore */ }
    setUser(null);
  }, []);

  const value = useMemo(
    () => ({ user, ready, isLogged: !!user, isAdmin: user?.acesso === 'admin', login, logout, refresh: () => setUser(api.getUser()) }),
    [user, ready, login, logout],
  );
  return <AuthCtx.Provider value={value}>{children}</AuthCtx.Provider>;
}

export const useAuth = () => useContext(AuthCtx);
