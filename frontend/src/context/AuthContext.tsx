import {
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { api, getAuthToken, setAuthToken } from "../services/api";
import type { AuthUser } from "../types/api";
import { AuthContext } from "./auth-context";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    // Purge legacy client-generated identity from localStorage
    localStorage.removeItem("projectops_user");

    async function checkSession() {
      const token = getAuthToken();
      if (!token) {
        setLoading(false);
        return;
      }

      try {
        const me = await api.getMe();
        setUser(me);
      } catch {
        setAuthToken(null);
        setUser(null);
      } finally {
        setLoading(false);
      }
    }

    void checkSession();

    function handleUnauthorized() {
      setUser(null);
      setAuthToken(null);
    }

    window.addEventListener("projectops:unauthorized", handleUnauthorized);
    return () => {
      window.removeEventListener("projectops:unauthorized", handleUnauthorized);
    };
  }, []);

  async function login(email: string, password: string) {
    await api.login(email, password);
    const me = await api.getMe();
    setUser(me);
  }

  async function register(email: string, displayName: string, password: string) {
    await api.register(email, displayName, password);
    await api.login(email, password);
    const me = await api.getMe();
    setUser(me);
  }

  function logout() {
    setAuthToken(null);
    localStorage.removeItem("projectops_user");
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}
