// Label tampilan untuk nilai enum dari backend.

import type { StatusSesi, TaskStatus } from "./api/types";

const LEVEL: Record<string, string> = { low: "Rendah", medium: "Sedang", high: "Tinggi" };

/** tingkat_effort / tingkat_impact ("low" | "medium" | "high") → label Indonesia. */
export function labelLevel(nilai: string | null | undefined): string {
  if (!nilai) return "—";
  return LEVEL[nilai.toLowerCase()] ?? nilai;
}

export const LABEL_STATUS_TASK: Record<TaskStatus, string> = {
  todo: "Belum mulai",
  in_progress: "Sedang dikerjakan",
  done: "Selesai",
};

export function labelStatusTask(status: string): string {
  return LABEL_STATUS_TASK[status as TaskStatus] ?? status;
}

export const LABEL_STATUS_SESI: Record<StatusSesi, string> = {
  terjadwal: "Terjadwal",
  selesai: "Selesai",
  dilewati: "Tidak dikerjakan",
  tidak_diketahui: "Perlu konfirmasi",
};
