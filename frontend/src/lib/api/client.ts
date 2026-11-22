import axios, { AxiosError } from "axios";

import { clearToken, getToken } from "../token";

// "/api/v1" = lewat proxy Next.js (next.config.ts); atau URL backend langsung bila CORS sudah aktif.
const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "/api/v1";

export const api = axios.create({
  baseURL: BASE_URL,
  timeout: 30_000,
});

// Decompose & rinci minggu memanggil LLM: timeout 90 dtk × retry di backend → bisa beberapa menit.
export const TIMEOUT_AI = 6 * 60_000;

api.interceptors.request.use((config) => {
  const token = getToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Jalur auth yang 401-nya adalah jawaban normal (password salah), bukan sesi kedaluwarsa.
const JALUR_AUTH = ["/auth/login", "/auth/register"];
// Halaman publik: token lama yang ditolak cukup dihapus, user tetap di halaman ini.
const HALAMAN_PUBLIK = ["/login", "/register"];

api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    const url = error.config?.url ?? "";
    if (
      error.response?.status === 401 &&
      !JALUR_AUTH.some((jalur) => url.endsWith(jalur)) &&
      typeof window !== "undefined"
    ) {
      // Token tidak valid / kedaluwarsa (JWT tidak punya refresh): kembali ke login,
      // lalu ke halaman semula setelah login.
      clearToken();
      if (!HALAMAN_PUBLIK.some((halaman) => window.location.pathname.startsWith(halaman))) {
        const next = window.location.pathname + window.location.search;
        // Sengaja full reload: interceptor bukan komponen (tidak bisa useRouter), dan reload
        // membuang seluruh state/cache React Query milik sesi yang sudah kedaluwarsa.
        // eslint-disable-next-line @next/next/no-location-assign-relative-destination
        window.location.assign(`/login?next=${encodeURIComponent(next)}`);
      }
    }
    return Promise.reject(error);
  }
);

// ============================================================
// Normalisasi error
// ============================================================

/** Satu jadwal yang ditabrak saat memindah sesi (409 PATCH /jadwal/sesi/{id}). */
export type Bentrok = {
  jenis: "rutin" | "agenda" | "task";
  nama: string;
  waktu_mulai: string;
  waktu_selesai: string;
  pesan: string;
};

export class ApiError extends Error {
  /** 0 = tidak ada respons (backend mati, jaringan, timeout). */
  readonly status: number;
  /** Isi 409 bentrok jadwal; kosong untuk error lain. */
  readonly bentrok: Bentrok[];
  /** Pesan validasi 422 per field (kunci = nama field terakhir di `loc`). */
  readonly fieldErrors: Record<string, string>;

  constructor(
    status: number,
    message: string,
    bentrok: Bentrok[] = [],
    fieldErrors: Record<string, string> = {}
  ) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.bentrok = bentrok;
    this.fieldErrors = fieldErrors;
  }
}

type ValidasiItem = { loc?: (string | number)[]; msg?: string };

// Pesan bawaan Pydantic (bahasa Inggris) yang paling sering muncul → bahasa Indonesia.
const TERJEMAHAN_PYDANTIC: [RegExp, (m: RegExpMatchArray) => string][] = [
  [/^value is not a valid email address/i, () => "Format email tidak valid"],
  [/^Field required$/i, () => "Wajib diisi"],
  [/^String should have at least (\d+) characters?$/i, (m) => `Minimal ${m[1]} karakter`],
  [/^String should have at most (\d+) characters?$/i, (m) => `Maksimal ${m[1]} karakter`],
  [/^Input should be greater than or equal to (\S+)$/i, (m) => `Minimal ${m[1]}`],
  [/^Input should be less than or equal to (\S+)$/i, (m) => `Maksimal ${m[1]}`],
  [/^Input should be a valid (date|time|datetime|integer|number)/i, () => "Format tidak valid"],
];

function bersihkanPesanPydantic(msg: string): string {
  // Pydantic menambah awalan "Value error, " pada ValueError dari validator (pesan kita sendiri).
  const bersih = msg.replace(/^Value error, /, "");
  for (const [pola, terjemah] of TERJEMAHAN_PYDANTIC) {
    const cocok = bersih.match(pola);
    if (cocok) return terjemah(cocok);
  }
  return bersih;
}

/** Ubah error apa pun dari axios menjadi ApiError dengan pesan yang siap ditampilkan. */
export function toApiError(error: unknown): ApiError {
  if (error instanceof ApiError) return error;

  if (!axios.isAxiosError(error)) {
    return new ApiError(0, error instanceof Error ? error.message : "Terjadi kesalahan");
  }

  if (!error.response) {
    if (error.code === "ECONNABORTED") {
      return new ApiError(0, "Server terlalu lama merespons. Coba lagi.");
    }
    return new ApiError(0, "Tidak bisa terhubung ke server. Pastikan backend berjalan.");
  }

  const { status, data } = error.response;
  const detail = (data as { detail?: unknown } | undefined)?.detail;

  // 1) detail string (bentuk paling umum dari HTTPException)
  if (typeof detail === "string") {
    return new ApiError(status, detail);
  }

  // 2) detail array: error validasi 422 FastAPI
  if (Array.isArray(detail)) {
    const fieldErrors: Record<string, string> = {};
    const pesan: string[] = [];
    for (const item of detail as ValidasiItem[]) {
      const msg = bersihkanPesanPydantic(item.msg ?? "Input tidak valid");
      const loc = (item.loc ?? []).filter((bagian) => bagian !== "body");
      const field = loc.length > 0 ? String(loc[loc.length - 1]) : "";
      if (field && !(field in fieldErrors)) fieldErrors[field] = msg;
      pesan.push(msg);
    }
    return new ApiError(status, pesan[0] ?? "Input tidak valid", [], fieldErrors);
  }

  // 3) detail objek: 409 bentrok jadwal {pesan, bentrok: [...]}
  if (detail && typeof detail === "object") {
    const obj = detail as { pesan?: unknown; bentrok?: unknown };
    const bentrok = Array.isArray(obj.bentrok) ? (obj.bentrok as Bentrok[]) : [];
    const pesan = typeof obj.pesan === "string" ? obj.pesan : "Permintaan ditolak server";
    return new ApiError(status, pesan, bentrok);
  }

  return new ApiError(status, pesanDefault(status));
}

function pesanDefault(status: number): string {
  if (status === 401) return "Sesi berakhir. Silakan masuk lagi.";
  if (status === 404) return "Data tidak ditemukan";
  if (status >= 500) return "Server sedang bermasalah. Coba lagi nanti.";
  return "Permintaan gagal";
}
