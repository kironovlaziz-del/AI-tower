"use client";

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";
import { useRouter } from "next/navigation";
import { clearToken, getMe, getToken, login as loginRequest, setToken } from "./api";
import type { User } from "./types";

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  login: (orgSlug: string, email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  const loadUser = useCallback(async () => {
    const token = getToken();
    if (!token) {
      setLoading(false);
      return;
    }
    try {
      const me = await getMe();
      setUser(me);
    } catch {
      clearToken();
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadUser();
  }, [loadUser]);

  const login = useCallback(
    async (orgSlug: string, email: string, password: string) => {
      const { access_token } = await loginRequest(orgSlug, email, password);
      setToken(access_token);
      const me = await getMe();
      setUser(me);
      // ui_mode is a personal preference (see backend PUT /users/me/ui-mode),
      // not a permission - it only decides where a fresh login lands.
      // null means "never chosen yet", so the person sees the one-time
      // chooser exactly once; after that we always remember their answer
      // rather than asking again (per the Simple Mode plan's own framing:
      // the choice happens at login, once).
      if (me.ui_mode === "simple") {
        router.push("/simple");
      } else if (me.ui_mode === "advanced") {
        router.push("/dashboard");
      } else {
        router.push("/choose-mode");
      }
    },
    [router]
  );

  const logout = useCallback(() => {
    clearToken();
    setUser(null);
    router.push("/login");
  }, [router]);

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}


