"use client";

import { useJadwalMinggu, useTimeConstraints } from "../../lib/api/queries";
import { MENIT_HARIAN_MAKS, MENIT_HARIAN_MIN, estimasiMenitHarian } from "../../lib/rencana";
import { awalMinggu, formatDurasi, formatJam, hariIniWib } from "../../lib/waktu";

export type EstimasiWaktu = {
  /** Menit luang per hari yang akan dipakai backend (sudah dibatasi), atau null bila belum termuat. */
  menit: number | null;
  /** Waktu luang di bawah batas minimum backend → dekomposisi tanpa override akan ditolak (422). */
  kurang: boolean;
  jamAktif: string | null;
};

/** Perkiraan menit_harian yang dihitung backend: jam aktif − kegiatan rutin (D6). */
export function useEstimasiWaktuLuang(): EstimasiWaktu {
  const rutin = useTimeConstraints();
  // jam aktif tidak punya endpoint sendiri; diambil dari respons kalender minggu ini
  const jadwal = useJadwalMinggu(awalMinggu(hariIniWib()));

  if (!rutin.data || !jadwal.data) return { menit: null, kurang: false, jamAktif: null };

  const { jam_aktif_mulai: mulai, jam_aktif_selesai: selesai } = jadwal.data;
  const mentah = estimasiMenitHarian(rutin.data, mulai, selesai);
  return {
    menit: Math.min(mentah, MENIT_HARIAN_MAKS),
    kurang: mentah < MENIT_HARIAN_MIN,
    jamAktif: `${formatJam(mulai)}–${formatJam(selesai)}`,
  };
}

export default function EstimasiWaktuLuang() {
  const { menit, kurang, jamAktif } = useEstimasiWaktuLuang();

  if (menit === null) {
    return <p className="text-sm text-[#8B857B]">Menghitung waktu luang...</p>;
  }

  return (
    <div>
      <p className="text-sm text-[#8B857B]">Perkiraan waktu luang per hari</p>
      <p className={`mt-1 text-2xl font-semibold ${kurang ? "text-[#8A3B2E]" : "text-[#506851]"}`}>
        {formatDurasi(menit)}
      </p>
      <p className="mt-1 text-xs text-[#8B857B]">
        Rata-rata seminggu dari jam aktif {jamAktif} dikurangi kegiatan rutinmu.
      </p>
      {kurang && (
        <p className="mt-2 text-xs text-[#8A3B2E]">
          Kurang dari {MENIT_HARIAN_MIN} menit per hari: kurangi kegiatan rutin atau isi waktu harian
          secara manual di langkah berikutnya.
        </p>
      )}
    </div>
  );
}
