import { api, TIMEOUT_AI } from "./client";
import type {
  DecomposeRequest,
  GoalCreate,
  GoalDetail,
  GoalRead,
  GoalUpdate,
  RincianMingguRead,
} from "./types";

export async function listGoals(): Promise<GoalRead[]> {
  const { data } = await api.get<GoalRead[]>("/goals");
  return data;
}

export async function getGoal(idGoal: number): Promise<GoalDetail> {
  const { data } = await api.get<GoalDetail>(`/goals/${idGoal}`);
  return data;
}

export async function createGoal(payload: GoalCreate): Promise<GoalRead> {
  const { data } = await api.post<GoalRead>("/goals", payload);
  return data;
}

export async function updateGoal(idGoal: number, payload: GoalUpdate): Promise<GoalRead> {
  const { data } = await api.patch<GoalRead>(`/goals/${idGoal}`, payload);
  return data;
}

export async function deleteGoal(idGoal: number): Promise<void> {
  await api.delete(`/goals/${idGoal}`);
}

/**
 * Susun rencana goal dengan AI (bulanan → mingguan, task minggu ke-1).
 * 409 = sudah didekomposisi (kirim `replace: true` untuk mengganti), 422 = waktu luang / deadline,
 * 502 = AI gagal. Bisa makan waktu beberapa menit.
 */
export async function decomposeGoal(
  idGoal: number,
  options: { menitHarian?: number | null; replace?: boolean } = {}
): Promise<GoalDetail> {
  const body: DecomposeRequest = { menit_harian: options.menitHarian ?? null };
  const { data } = await api.post<GoalDetail>(`/goals/${idGoal}/decompose`, body, {
    params: options.replace ? { replace: true } : undefined,
    timeout: TIMEOUT_AI,
  });
  return data;
}

/**
 * Rinci task minggu ini / depan dengan AI. Idempotent (`baru: false` bila sudah dirinci).
 * `depan` baru boleh mulai Sabtu (409). Tidak menjadwalkan: panggil jadwalkanGoal sesudahnya.
 */
export async function rinciMinggu(
  idGoal: number,
  minggu: "ini" | "depan",
  menitHarian?: number | null
): Promise<RincianMingguRead> {
  const body: DecomposeRequest = { menit_harian: menitHarian ?? null };
  const { data } = await api.post<RincianMingguRead>(`/goals/${idGoal}/rinci-minggu`, body, {
    params: { minggu },
    timeout: TIMEOUT_AI,
  });
  return data;
}
