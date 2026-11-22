// Statistik halaman Analitik dari GET /tasks (fungsi murni, tanggal dalam WIB).

import type { TaskRead } from "./api/types";
import { selisihHari } from "./kalender";
import { tanggalDari } from "./waktu";

export type Level = "high" | "medium" | "low";
export const LEVEL: Level[] = ["high", "medium", "low"];

export type StatistikTask = {
  total: number;
  selesai: number;
  sedang: number;
  belum: number;
  /** persen task selesai (0–100, dibulatkan) */
  persenSelesai: number;
  /** jumlah task per tingkat impact / effort; nilai kosong / tak dikenal masuk `lainnya` */
  impact: Record<Level, number> & { lainnya: number };
  effort: Record<Level, number> & { lainnya: number };
  /** belum selesai & deadline-nya sebelum hari ini */
  terlambat: number;
  /** belum selesai & deadline hari ini s/d 7 hari ke depan */
  tujuhHari: number;
  /** maks 5 task impact tinggi yang belum selesai, deadline terdekat dulu (tanpa deadline di akhir) */
  prioritasUtama: TaskRead[];
};

function hitungLevel(tasks: TaskRead[], ambil: (t: TaskRead) => string | null) {
  const hasil = { high: 0, medium: 0, low: 0, lainnya: 0 };
  for (const t of tasks) {
    const nilai = (ambil(t) ?? "").toLowerCase();
    if (nilai === "high" || nilai === "medium" || nilai === "low") hasil[nilai] += 1;
    else hasil.lainnya += 1;
  }
  return hasil;
}

export function statistikTask(tasks: TaskRead[], hariIni: string): StatistikTask {
  const selesai = tasks.filter((t) => t.status === "done").length;
  const sedang = tasks.filter((t) => t.status === "in_progress").length;
  const aktif = tasks.filter((t) => t.status !== "done");

  const sisaHari = (t: TaskRead) => (t.deadline ? selisihHari(hariIni, tanggalDari(t.deadline)) : null);

  const prioritasUtama = aktif
    .filter((t) => t.tingkat_impact?.toLowerCase() === "high")
    .sort((a, b) => {
      if (!a.deadline) return b.deadline ? 1 : a.id_task - b.id_task;
      if (!b.deadline) return -1;
      return a.deadline.localeCompare(b.deadline) || a.id_task - b.id_task;
    })
    .slice(0, 5);

  return {
    total: tasks.length,
    selesai,
    sedang,
    belum: tasks.length - selesai - sedang,
    persenSelesai: tasks.length ? Math.round((selesai / tasks.length) * 100) : 0,
    impact: hitungLevel(tasks, (t) => t.tingkat_impact),
    effort: hitungLevel(tasks, (t) => t.tingkat_effort),
    terlambat: aktif.filter((t) => {
      const sisa = sisaHari(t);
      return sisa !== null && sisa < 0;
    }).length,
    tujuhHari: aktif.filter((t) => {
      const sisa = sisaHari(t);
      return sisa !== null && sisa >= 0 && sisa <= 7;
    }).length,
    prioritasUtama,
  };
}
