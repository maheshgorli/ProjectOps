
import {
  createContext,
  useContext,
  useState,
  type ReactNode,
} from "react";

type User = {
  id: string;
  name: string;
  email: string;
};

type AuthContextType = {
  user: User | null;
  login: (name: string, email: string) => void;
  logout: () => void;
};

const AuthContext = createContext<AuthContextType | null>(null);

function getSavedUser(): User | null {
  try {
    const saved = localStorage.getItem("projectops_user");
    return saved ? (JSON.parse(saved) as User) : null;
  } catch {
    return null;
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(getSavedUser);

  function login(name: string, email: string) {
    const nextUser: User = {
      id: crypto.randomUUID(),
      name: name.trim(),
      email: email.trim().toLowerCase(),
    };

    localStorage.setItem("projectops_user", JSON.stringify(nextUser));
    setUser(nextUser);
  }

  function logout() {
    localStorage.removeItem("projectops_user");
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ user, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error("useAuth must be used inside AuthProvider");
  }

  return context;
}
