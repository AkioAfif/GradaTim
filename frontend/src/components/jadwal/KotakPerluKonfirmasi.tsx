"use client";

import { AlertCircle } from "lucide-react";

import type { SesiRead } from "../../lib/api/types";
import SesiCard from "./SesiCard";

/**
 * Sesi yang sudah mulai/terlewat dan belum dikonfirmasi — sumber label model personalisasi
 * (docs/AI.md §2), jadi ditampilkan paling menonjol. Tidak merender apa pun bila kosong.
 */
export default function KotakPerluKonfirmasi({
  sesi,
  sekarang,
  id,
}: {
  sesi: SesiRead[];
  sekarang: Date;
  id?: string;
}) {
  if (sesi.length === 0) return null;
  return (
    <section id={id} className="scroll-mt-6 rounded-xl border-2 border-[#D9A441] bg-[#FFF8EA] p-5">
      <h2 className="flex items-center gap-2 text-base font-semibold text-[#6B4E12]">
        <AlertCircle size={18} /> {sesi.length} sesi perlu dikonfirmasi
      </h2>
      <p className="mt-1 text-sm text-[#7A5A1E]">
        Apakah sesi ini kamu kerjakan? Konfirmasi bisa sampai 48 jam setelah sesi berakhir.
      </p>
      <div className="mt-4 grid gap-3 md:grid-cols-2">
        {sesi.map((s) => (
          <SesiCard key={s.id_jadwal} sesi={s} sekarang={sekarang} tampilTanggal />
        ))}
      </div>
    </section>
  );
}
