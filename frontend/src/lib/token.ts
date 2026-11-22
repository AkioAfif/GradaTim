// Penyimpanan JWT di localStorage. Semua akses dibungkus try/catch: localStorage bisa
// tidak tersedia (mode privat, storage diblokir) dan tidak ada saat render di server.

const TOKEN_KEY = "gradatim-token";

export function getToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setToken(token: string): void {
  try {
    localStorage.setItem(TOKEN_KEY, token);
  } catch {
    // tetap login selama tab terbuka lewat state AuthContext
  }
}

export function clearToken(): void {
  try {
    localStorage.removeItem(TOKEN_KEY);
  } catch {
    // abaikan
  }
}
