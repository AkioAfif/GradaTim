import { api } from "./client";
import type {
  HasilPenjadwalanRead,
  HasilSusunUlangRead,
  JadwalMingguan,
  SesiRead,
  SesiUpdate,
  SusunUlangRequest,
  TanggalStr,
} from "./types";

/** Isi kalender satu minggu (Senin–Minggu) yang memuat `minggu`; default minggu ini. */
export async function getJadwalMinggu(minggu?: TanggalStr): Promise<JadwalMingguan> {
  const { data } = await api.get<JadwalMingguan>("/jadwal", {
    params: minggu ? { minggu } : undefined,
  });
  return data;
}

/** Jadwalkan task goal yang belum terjadwal ke slot luang minggu ini. Aman dipanggil berulang. */
export async function jadwalkanGoal(idGoal: number): Promise<HasilPenjadwalanRead> {
  const { data } = await api.post<HasilPenjadwalanRead>(`/jadwal/goal/${idGoal}`);
  return data;
}

/**
 * Susun ulang minggu ini: sesi terlewat → `tidak_diketahui` lalu dijadwalkan ulang;
 * `ditunda` = id_task yang ditunda karena mood (dipindah mulai besok).
 */
export async function susunUlang(payload: SusunUlangRequest = {}): Promise<HasilSusunUlangRead> {
  const { data } = await api.post<HasilSusunUlangRead>("/jadwal/susun-ulang", payload);
  return data;
}

/** Konfirmasi status sesi dan/atau pindah waktu. 409 → lihat ApiError.bentrok / pesan aturan. */
export async function ubahSesi(idJadwal: number, payload: SesiUpdate): Promise<SesiRead> {
  const { data } = await api.patch<SesiRead>(`/jadwal/sesi/${idJadwal}`, payload);
  return data;
}
