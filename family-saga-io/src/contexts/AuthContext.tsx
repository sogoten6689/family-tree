import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { fetchCurrentUser, loginUser, registerUser } from "@/lib/authApi";
import type { AuthSession, User } from "@/types/auth";

const AUTH_STORAGE_KEY = "family_tree_auth";

interface AuthContextValue {
  user: User | null;
  accessToken: string | null;
  isAuthenticated: boolean;
  isAdmin: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (payload: { email: string; password: string; full_name: string }) => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

function readStoredSession(): AuthSession | null {
  try {
    const raw = localStorage.getItem(AUTH_STORAGE_KEY);
    if (!raw) return null;
    return JSON.parse(raw) as AuthSession;
  } catch {
    return null;
  }
}

function persistSession(session: AuthSession | null) {
  if (!session) {
    localStorage.removeItem(AUTH_STORAGE_KEY);
    return;
  }
  localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(session));
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const stored = readStoredSession();
    if (!stored?.accessToken) {
      setIsLoading(false);
      return;
    }

    setAccessToken(stored.accessToken);
    setUser(stored.user);

    fetchCurrentUser(stored.accessToken)
      .then((currentUser) => {
        setUser(currentUser);
        persistSession({ accessToken: stored.accessToken, user: currentUser });
      })
      .catch(() => {
        persistSession(null);
        setAccessToken(null);
        setUser(null);
      })
      .finally(() => setIsLoading(false));
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const result = await loginUser({ email, password });
    const session = { accessToken: result.access_token, user: result.user };
    persistSession(session);
    setAccessToken(result.access_token);
    setUser(result.user);
  }, []);

  const register = useCallback(
    async (payload: { email: string; password: string; full_name: string }) => {
      await registerUser(payload);
    },
    [],
  );

  const logout = useCallback(() => {
    persistSession(null);
    setAccessToken(null);
    setUser(null);
  }, []);

  const refreshUser = useCallback(async () => {
    if (!accessToken) return;
    const currentUser = await fetchCurrentUser(accessToken);
    setUser(currentUser);
    persistSession({ accessToken, user: currentUser });
  }, [accessToken]);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      accessToken,
      isAuthenticated: !!accessToken && !!user,
      isAdmin: user?.role === "admin",
      isLoading,
      login,
      register,
      logout,
      refreshUser,
    }),
    [user, accessToken, isLoading, login, register, logout, refreshUser],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}
