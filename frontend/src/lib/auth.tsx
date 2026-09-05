import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { api } from "../api/client";

export type User = {
  id: string;
  email: string;
  full_name: string | null;
  role: string;
  created_at: string;
};

type AuthContextValue = {
  user: User | null;
  loading: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signUp: (
    email: string,
    password: string,
    fullName: string
  ) => Promise<void>;
  signOut: () => void;
};

const TOKEN_KEY = "medlens_token";
const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  // On reload, ask the API who the stored token belongs to.
  useEffect(() => {
    const token = localStorage.getItem(TOKEN_KEY);
    if (!token) {
      setLoading(false);
      return;
    }
    api
      .get<User>("/api/auth/me")
      .then((r) => setUser(r.data))
      .catch(() => localStorage.removeItem(TOKEN_KEY))
      .finally(() => setLoading(false));
  }, []);

  const signIn = useCallback(async (email: string, password: string) => {
    const { data } = await api.post("/api/auth/login", { email, password });
    localStorage.setItem(TOKEN_KEY, data.access_token);
    setUser(data.user);
  }, []);

  const signUp = useCallback(
    async (email: string, password: string, fullName: string) => {
      const { data } = await api.post("/api/auth/register", {
        email,
        password,
        full_name: fullName || null,
      });
      localStorage.setItem(TOKEN_KEY, data.access_token);
      setUser(data.user);
    },
    []
  );

  const signOut = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    setUser(null);
  }, []);

  const value = useMemo(
    () => ({ user, loading, signIn, signUp, signOut }),
    [user, loading, signIn, signUp, signOut]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}

/** Turns an axios failure into something worth showing a person. */
export function errorMessage(err: unknown): string {
  const e = err as { response?: { data?: { detail?: unknown } } };
  const detail = e?.response?.data?.detail;

  if (typeof detail === "string") return detail;

  // FastAPI validation errors arrive as an array.
  if (Array.isArray(detail) && detail.length > 0) {
    const first = detail[0] as { msg?: string };
    if (first?.msg) return first.msg.replace(/^Value error, /, "");
  }

  return "Could not reach the server. Check that the backend is running.";
}
