"use client";

import { useState } from "react";

import DashboardLayout from "../../components/DashboardLayout";
import UserAvatar from "../../components/UserAvatar";
import { useSekarang } from "../../components/jadwal/hooks";
import HasilMood from "../../components/mood/HasilMood";
import KuesionerMood from "../../components/mood/KuesionerMood";
import { errorBoxClass, secondaryButtonClass, warningBoxClass } from "../../components/ui";
import { ApiError } from "../../lib/api/client";
import { useJadwalMinggu, useMoodHariIni } from "../../lib/api/queries";
import { sesiPadaTanggal } from "../../lib/sesi";
import { awalMinggu, formatJam, formatTanggal, hariIniWib, parseWib } from "../../lib/waktu";

export default function MoodPage() {
  const hariIni = hariIniWib();
  const sekarang = useSekarang();
  const mood = useMoodHariIni();
  const jadwal = useJadwalMinggu(awalMinggu(hariIni));
  const [isiUlang, setIsiUlang] = useState(false);

  // Mood dipakai sebagai fitur model hanya untuk sesi yang mulai SETELAH mood diisi (docs/AI.md §2).
  const sesiSudahMulai = sesiPadaTanggal(jadwal.data?.sesi ?? [], hariIni).filter(
    (s) => parseWib(s.waktu_mulai).getTime() <= sekarang.getTime()
  );
  const tampilForm = mood.data === null || isiUlang;

  return (
    <DashboardLayout>
      <div className="mx-auto max-w-3xl">
        <header className="flex items-center justify-between border-b border-[#E9E0D4] pb-5">
          <p className="text-xs text-[#8B857B]">Mood</p>
          <UserAvatar />
        </header>

        <section className="mt-7 flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="text-xs font-bold tracking-[0.12em] text-[#506851]">MOOD HARIAN</p>
            <h1 className="mt-3 text-3xl font-medium tracking-tight md:text-4xl">Bagaimana kondisimu?</h1>
            <p className="mt-3 text-sm text-[#8B857B]">
              {formatTanggal(hariIni)} · 5 pertanyaan singkat untuk menyesuaikan task hari ini dengan kondisimu.
            </p>
          </div>
          {mood.data && !isiUlang && (
            <button type="button" onClick={() => setIsiUlang(true)} className={secondaryButtonClass}>
              Isi ulang
            </button>
          )}
        </section>

        {tampilForm && sesiSudahMulai.length > 0 && (
          <p className={`mt-6 ${warningBoxClass}`}>
            Sesi pertama hari ini sudah dimulai pukul {formatJam(sesiSudahMulai[0].waktu_mulai)}. Besok, coba isi mood
            pagi hari sebelum sesi pertama supaya rekomendasinya paling akurat.
          </p>
        )}

        <div className="mt-6">
          {mood.isPending ? (
            <p className="text-sm text-[#8B857B]">Memuat...</p>
          ) : mood.isError ? (
            <p role="alert" className={errorBoxClass}>
              {mood.error instanceof ApiError && mood.error.status === 503
                ? "Layanan penilaian mood sedang tidak tersedia. Coba lagi beberapa saat lagi."
                : mood.error.message}
            </p>
          ) : tampilForm ? (
            <KuesionerMood
              key={isiUlang ? "ulang" : "baru"}
              awal={isiUlang ? mood.data?.jawaban : undefined}
              onBatal={isiUlang ? () => setIsiUlang(false) : undefined}
              onTersimpan={() => setIsiUlang(false)}
            />
          ) : (
            mood.data && <HasilMood mood={mood.data} />
          )}
        </div>
      </div>
    </DashboardLayout>
  );
}
