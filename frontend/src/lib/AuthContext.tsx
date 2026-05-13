"use client";

import { createContext, useContext, useEffect, useState, useCallback } from "react";
import { loginUser, registerUser, fetchProfile } from "./api";

interface UserProfile {
  id: number;
  email: string;
  full_name: string;
}

interface AuthContextType {
  user: UserProfile | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);

  // On mount, check for saved token and validate it
  useEffect(() => {
    const token = localStorage.getItem("trustguard_token");
    if (!token) {
      setLoading(false);
      return;
    }
    fetchProfile()
      .then((profile) => setUser(profile))
      .catch(() => {
        localStorage.removeItem("trustguard_token");
      })
      .finally(() => setLoading(false));
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const data = await loginUser(email, password);
    localStorage.setItem("trustguard_token", data.access_token);
    const profile = await fetchProfile();
    setUser(profile);
  }, []);

  const register = useCallback(async (email: string, password: string, fullName: string) => {
    await registerUser(email, password, fullName);
    // Auto-login after registration
    const data = await loginUser(email, password);
    localStorage.setItem("trustguard_token", data.access_token);
    const profile = await fetchProfile();
    setUser(profile);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem("trustguard_token");
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
