import { api } from "./client";
import type { Token, UserCreate, UserLogin, UserRead } from "./types";

export async function register(payload: UserCreate): Promise<UserRead> {
  const { data } = await api.post<UserRead>("/auth/register", payload);
  return data;
}

export async function login(payload: UserLogin): Promise<Token> {
  const { data } = await api.post<Token>("/auth/login", payload);
  return data;
}

export async function me(): Promise<UserRead> {
  const { data } = await api.get<UserRead>("/auth/me");
  return data;
}
