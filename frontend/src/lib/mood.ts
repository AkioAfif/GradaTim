// Kuesioner mood harian (FR-6). Teks & arti skala sama dengan data latih model mood
// (backend/ai_model/generate_data.py): skala 1–5, urutan = nomor_questionnaire 1–5.

import type { MoodAnswers } from "./api/types";

export type PertanyaanMood = {
  kunci: keyof MoodAnswers;
  teks: string;
  /** arti nilai 1 */
  rendah: string;
  /** arti nilai 5 */
  tinggi: string;
};

export const PERTANYAAN_MOOD: PertanyaanMood[] = [
  { kunci: "q1_focus", teks: "Seberapa fokus kamu hari ini?", rendah: "Sangat tidak fokus", tinggi: "Sangat fokus" },
  { kunci: "q2_calm", teks: "Seberapa tenang perasaanmu?", rendah: "Sangat cemas", tinggi: "Sangat tenang" },
  { kunci: "q3_motivated", teks: "Seberapa termotivasi kamu?", rendah: "Tidak sama sekali", tinggi: "Sangat termotivasi" },
  { kunci: "q4_sleep", teks: "Seberapa cukup tidurmu semalam?", rendah: "Sangat kurang", tinggi: "Sangat cukup" },
  { kunci: "q5_readiness", teks: "Seberapa siap kamu menghadapi tugas?", rendah: "Tidak siap", tinggi: "Sangat siap" },
];

export type JawabanSebagian = Partial<Record<keyof MoodAnswers, number>>;

/** Semua pertanyaan terjawab dengan nilai 1–5 → MoodAnswers; selain itu null. */
export function jawabanLengkap(jawaban: JawabanSebagian): MoodAnswers | null {
  const hasil: Partial<MoodAnswers> = {};
  for (const { kunci } of PERTANYAAN_MOOD) {
    const nilai = jawaban[kunci];
    if (nilai === undefined || !Number.isInteger(nilai) || nilai < 1 || nilai > 5) return null;
    hasil[kunci] = nilai;
  }
  return hasil as MoodAnswers;
}
