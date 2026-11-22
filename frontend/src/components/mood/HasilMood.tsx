"use client";

import { useState } from "react";
import Link from "next/link";
import { Smile } from "lucide-react";

import HasilSusunUlang from "../jadwal/HasilSusunUlang";
import { useSekarang, useSusunUlang } from "../jadwal/hooks";
import { errorBoxClass, infoBoxClass, primaryButtonClass, warningBoxClass } from "../ui";
import type { MoodHariIni, TaskRekomendasi } from "../../lib/api/types";
import { LABEL_KAPASITAS, labelLevel } from "../../lib/label";
import { formatRentangJam, hariDalamMinggu, hariIniWib } from "../../lib/waktu";

const WARNA_KAPASITAS: Record<string, string> = {
  LOW: "border-[#D9A441] bg-[#FFF8EA] text-[#6B4E12]",
  MEDIUM: "border-[#B9C7B1] bg-[#F1F5EE] text-[#3E5340]",
  HIGH: "border-[#82947B] bg-[#E8EFE4] text-[#30412F]",
};

function ItemTask({ task }: { task: TaskRekomendasi }) {
  return (
    <div className="min-w-0">
      <p className="text-sm font-medium">{task.nama_task}</p>
      <p className="mt-0.5 text-xs text-[#8B857B]">
        {task.sesi.map((s) => formatRentangJam(s.waktu_mulai, s.waktu_selesai)).join(", ")}
        {" · "}Effort {labelLevel(task.tingkat_effort)} · Impact {labelLevel(task.tingkat_impact)}
      </p>
    </div>
  );
}

/** Hasil mood + rekomendasi task hari ini (FR-7), dengan opsi menunda task yang disarankan. */
export default function HasilMood({ mood }: { mood: MoodHariIni }) {
  const sekarang = useSekarang();
  const { hasil, rekomendasi } = mood;
  const ditundaSaran = rekomendasi.disarankan_ditunda;
  // default: semua saran ditunda tercentang; user boleh mempertahankan sebagian
  const [tidakDitunda, setTidakDitunda] = useState<Set<number>>(new Set());
  const tunda = useSusunUlang();

  const dipilih = ditundaSaran.filter((t) => !tidakDitunda.has(t.id_task)).map((t) => t.id_task);
  // susun ulang hanya menjadwalkan ulang di dalam minggu berjalan (Senin–Minggu)
  const hariTerakhirMinggu = hariDalamMinggu(hariIniWib()) === 6;

  function toggle(idTask: number) {
    setTidakDitunda((sebelum) => {
      const baru = new Set(sebelum);
      if (baru.has(idTask)) baru.delete(idTask);
      else baru.add(idTask);
      return baru;
    });
  }

  return (
    <div className="space-y-5">
      <section className={`rounded-xl border p-5 ${WARNA_KAPASITAS[hasil.capacity_level] ?? WARNA_KAPASITAS.MEDIUM}`}>
        <div className="flex items-start gap-3">
          <Smile size={24} className="mt-0.5 shrink-0" />
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide opacity-80">Kapasitas hari ini</p>
            <p className="mt-1 text-2xl font-semibold">
              {LABEL_KAPASITAS[hasil.capacity_level] ?? hasil.capacity_level}
            </p>
            <p className="mt-2 text-sm">{hasil.recommendation_message}</p>
            <p className="mt-2 text-xs opacity-80">Disarankan maksimal {hasil.max_tasks} task hari ini.</p>
          </div>
        </div>
      </section>

      <section className="rounded-xl border border-[#E7DBCC] bg-[#FFFCF7] p-5">
        <h2 className="text-base font-semibold">Dikerjakan hari ini</h2>
        {rekomendasi.direkomendasikan.length === 0 ? (
          <p className="mt-2 text-sm text-[#8B857B]">
            {ditundaSaran.length === 0
              ? "Tidak ada sesi task tersisa hari ini."
              : "Tidak ada task yang direkomendasikan hari ini."}
          </p>
        ) : (
          <ol className="mt-3 space-y-3">
            {rekomendasi.direkomendasikan.map((t, i) => (
              <li key={t.id_task} className="flex gap-3">
                <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-[#506851] text-xs font-semibold text-white">
                  {i + 1}
                </span>
                <ItemTask task={t} />
              </li>
            ))}
          </ol>
        )}
      </section>

      {ditundaSaran.length > 0 && (
        <section className="rounded-xl border border-[#E7DBCC] bg-[#FFFCF7] p-5">
          <h2 className="text-base font-semibold">Disarankan ditunda</h2>
          <p className="mt-1 text-sm text-[#8B857B]">
            Sesuai kondisimu, task ini sebaiknya tidak dikerjakan hari ini. Task tidak hilang: sesinya dipindah ke
            slot kosong berikutnya di minggu ini, mulai besok.
          </p>
          {hariTerakhirMinggu && (
            <p className={`mt-3 ${warningBoxClass}`}>
              Hari ini hari terakhir minggu ini, jadi task yang ditunda belum mendapat sesi baru. Jadwalkan lagi
              minggu depan lewat tombol &quot;Jadwalkan&quot; di halaman goal-nya.
            </p>
          )}
          <ul className="mt-4 space-y-3">
            {ditundaSaran.map((t) => (
              <li key={t.id_task}>
                <label className="flex cursor-pointer items-start gap-3">
                  <input
                    type="checkbox"
                    checked={!tidakDitunda.has(t.id_task)}
                    disabled={tunda.isPending}
                    onChange={() => toggle(t.id_task)}
                    className="mt-1 h-4 w-4 shrink-0 accent-[#826049]"
                  />
                  <ItemTask task={t} />
                </label>
              </li>
            ))}
          </ul>
          <button
            type="button"
            disabled={tunda.isPending || dipilih.length === 0}
            onClick={() => tunda.mutate({ ditunda: dipilih })}
            className={`mt-5 ${primaryButtonClass}`}
          >
            {tunda.isPending
              ? "Menunda..."
              : dipilih.length === 0
                ? "Pilih task yang ingin ditunda"
                : `Tunda ${dipilih.length} task`}
          </button>
          {tunda.isError && (
            <p role="alert" className={`mt-3 ${errorBoxClass}`}>
              {tunda.error.message}
            </p>
          )}
        </section>
      )}

      {tunda.isSuccess && (
        <section className="space-y-3">
          <p className={infoBoxClass}>Task yang ditunda sudah dipindah. Rekomendasi di atas ikut diperbarui.</p>
          <HasilSusunUlang hasil={tunda.data} sekarang={sekarang} />
        </section>
      )}

      <p className="text-sm text-[#8B857B]">
        Lihat semua sesi di{" "}
        <Link href="/calendar" className="font-medium text-[#506851] underline">
          kalender
        </Link>
        .
      </p>
    </div>
  );
}
