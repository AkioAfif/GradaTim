import { api } from "./client";
import type { MoodAnswers, MoodHariIni } from "./types";

/** Isi kuesioner hari ini (menimpa isian sebelumnya di hari yang sama). 503 = model mood gagal. */
export async function isiMood(payload: MoodAnswers): Promise<MoodHariIni> {
  const { data } = await api.post<MoodHariIni>("/mood", payload);
  return data;
}

/** Hasil mood hari ini; 404 = belum diisi. */
export async function getMoodHariIni(): Promise<MoodHariIni> {
  const { data } = await api.get<MoodHariIni>("/mood/hari-ini");
  return data;
}
