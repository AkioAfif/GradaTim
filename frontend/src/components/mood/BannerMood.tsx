"use client";

import Link from "next/link";
import { Smile, SunMedium } from "lucide-react";

import type { MoodHariIni, SesiRead } from "../../lib/api/types";
import { LABEL_KAPASITAS } from "../../lib/label";
import { formatJam } from "../../lib/waktu";

/**
 * Pengingat kuesioner mood. Mood sebaiknya diisi pagi, sebelum sesi pertama dimulai: mood yang
 * diisi setelah sesi mulai tidak dipakai sebagai fitur model untuk sesi itu (docs/AI.md §2).
 */
export default function BannerMood({
  mood,
  sesiBerikutnya,
  memuat,
}: {
  /** null = belum diisi hari ini; undefined = belum termuat / gagal dimuat */
  mood: MoodHariIni | null | undefined;
  sesiBerikutnya: SesiRead | null;
  memuat: boolean;
}) {
  if (memuat || mood === undefined) return null;

  if (mood === null) {
    return (
      <section className="flex flex-col gap-4 rounded-xl border border-[#D7B99B] bg-[#FBF1E6] p-5 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-start gap-3">
          <SunMedium size={22} className="mt-0.5 shrink-0 text-[#826049]" />
          <div>
            <p className="font-semibold text-[#45382E]">Bagaimana kondisimu hari ini?</p>
            <p className="mt-1 text-sm text-[#6D4D38]">
              {sesiBerikutnya
                ? `Isi kuesioner mood (5 pertanyaan) sebelum sesi pertama pukul ${formatJam(sesiBerikutnya.waktu_mulai)} supaya rekomendasi task hari ini sesuai kondisimu.`
                : "Isi kuesioner mood (5 pertanyaan) untuk mendapat rekomendasi task hari ini."}
            </p>
          </div>
        </div>
        <Link
          href="/mood"
          className="shrink-0 self-start rounded-lg bg-[#826049] px-5 py-2.5 text-sm font-medium text-white hover:bg-[#6D4D38] sm:self-auto"
        >
          Isi mood
        </Link>
      </section>
    );
  }

  const { hasil, rekomendasi } = mood;
  return (
    <section className="flex flex-col gap-3 rounded-xl border border-[#D5DFCE] bg-[#F1F5EE] p-5 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex items-start gap-3">
        <Smile size={22} className="mt-0.5 shrink-0 text-[#506851]" />
        <div>
          <p className="font-semibold text-[#3E5340]">
            Kapasitas hari ini: {LABEL_KAPASITAS[hasil.capacity_level] ?? hasil.capacity_level}
          </p>
          <p className="mt-1 text-sm text-[#506851]">{hasil.recommendation_message}</p>
          {rekomendasi.disarankan_ditunda.length > 0 && (
            <p className="mt-1 text-sm text-[#7A5A1E]">
              {rekomendasi.disarankan_ditunda.length} task disarankan ditunda.
            </p>
          )}
        </div>
      </div>
      <Link href="/mood" className="shrink-0 self-start text-sm font-medium text-[#506851] underline sm:self-auto">
        Lihat rekomendasi
      </Link>
    </section>
  );
}
