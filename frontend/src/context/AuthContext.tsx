"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { useQueryClient } from "@tanstack/react-query";

import * as authApi from "../lib/api/auth";
import { toApiError } from "../lib/api/client";
import type { UserCreate, UserLogin, UserRead } from "../lib/api/types";
import { clearToken, getToken, setToken } from "../lib/token";

/**
 * - loading: token sedang diperiksa (render awal, server maupun client)
 * - authenticated: token valid, `user` terisi
 * - unauthenticated: tidak ada token / token ditolak
 * - error: token ada tapi /auth/me gagal karena hal lain (mis. backend mati) — token TIDAK dihapus
 */
export type AuthStatus = "loading" | "authenticated" | "unauthenticated" | "error";

type AuthContextType = {
  status: AuthStatus;
  user: UserRead | null;
  errorMessage: string | null;
  /** true bila status unauthenticated karena user menekan Keluar (bukan sesi kedaluwarsa). */
  keluarManual: boolean;
  login: (payload: UserLogin) => Promise<void>;
  register: (payload: UserCreate) => Promise<void>;
  logout: () => void;
  retry: () => void;
};

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [status, setStatus] = useState<AuthStatus>("loading");
  const [user, setUser] = useState<UserRead | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [keluarManual, setKeluarManual] = useState(false);

  const muatUser = useCallback(async () => {
    if (!getToken()) {
      setUser(null);
      setStatus("unauthenticated");
      return;
    }
    setStatus("loading");
    try {
      const data = await authApi.me();
      setUser(data);
      setErrorMessage(null);
      setStatus("authenticated");
    } catch (error) {
      const apiError = toApiError(error);
      if (apiError.status === 401) {
        clearToken();
        setUser(null);
        setStatus("unauthenticated");
      } else {
        setErrorMessage(apiError.message);
        setStatus("error");
      }
    }
  }, []);

  useEffect(() => {
    // Token baru bisa dibaca di browser; muatUser mengubah state setelah request selesai.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void muatUser();
  }, [muatUser]);

  const login = useCallback(
    async (payload: UserLogin) => {
      try {
        const token = await authApi.login(payload);
        setToken(token.access_token);
      } catch (error) {
        throw toApiError(error);
      }
      queryClient.clear(); // jangan bawa cache user sebelumnya
      setKeluarManual(false);
      await muatUser();
    },
    [muatUser, queryClient]
  );

  const register = useCallback(
    async (payload: UserCreate) => {
      try {
        await authApi.register(payload);
      } catch (error) {
        throw toApiError(error);
      }
      await login({ email: payload.email, password: payload.password });
    },
    [login]
  );

  const logout = useCallback(() => {
    clearToken();
    queryClient.clear();
    setUser(null);
    setKeluarManual(true);
    setStatus("unauthenticated");
  }, [queryClient]);

  const value = useMemo(
    () => ({
      status,
      user,
      errorMessage,
      keluarManual,
      login,
      register,
      logout,
      retry: () => void muatUser(),
    }),
    [status, user, errorMessage, keluarManual, login, register, logout, muatUser]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth harus digunakan di dalam AuthProvider");
  }
  return context;
}
