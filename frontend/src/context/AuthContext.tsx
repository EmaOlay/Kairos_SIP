import React, { createContext, useContext, useEffect, useState } from 'react';
import {
  authService,
  clearStoredToken,
  getStoredToken,
  setStoredToken,
} from '../services/authService';
import type { User } from '../services/authService';

interface AuthContextValue {
  user: User | null;
  token: string | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(() => getStoredToken());
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    let cancelled = false;
    const stored = getStoredToken();

    // si no hay token, no hay nada que revalidar
    if (!stored) {
      setLoading(false);
      return;
    }

    (async () => {
      try {
        const me = await authService.me(stored);
        if (cancelled) return;
        setUser(me);
        setToken(stored);
      } catch {
        // token inválido o expirado: lo tiramos a la basura
        if (cancelled) return;
        clearStoredToken();
        setUser(null);
        setToken(null);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  const login = async (username: string, password: string) => {
    const resp = await authService.login(username, password);
    setStoredToken(resp.access_token);
    setToken(resp.access_token);
    setUser(resp.user);
  };

  const logout = () => {
    clearStoredToken();
    setToken(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, token, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth tiene que usarse adentro de un <AuthProvider>');
  }
  return ctx;
}
