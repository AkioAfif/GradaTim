"use client";

import type { HasilSusunUlangRead, SesiRead } from "../../lib/api/types";
import { infoBoxClass, warningBoxClass } from "../ui";
import SesiCard from "./SesiCard";

/**
 * Ringkasan POST /jadwal/susun-ulang. Sesi terlewat langsung bisa dikonfirmasi di sini.
 * `sesiTerkini` (id_jadwal → sesi dari kalender yang selalu di-refetch) menggantikan data respons
 * yang sekali jadi, supaya status kartu ikut berubah setelah dikonfirmasi.
 */
export default function HasilSusunUlang({
  hasil,
  sekarang,
  sesiTerkini,
}: {
  hasil: HasilSusunUlangRead;
  sekarang: Date;
  sesiTerkini?: Map<number, SesiRead>;
}) {
  const kosong =
    hasil.dipindah.length === 0 && hasil.tidak_muat.length === 0 && hasil.sesi_terlewat.length === 0;

  if (kosong) {
    return <p className={infoBoxClass}>Jadwal minggu ini sudah rapi. Tidak ada yang perlu disusun ulang.</p>;
  }

  return (
    <div className="space-y-4">
      {hasil.dipindah.length > 0 && (
        <div className={infoBoxClass}>
          <p className="font-medium">{hasil.dipindah.length} task dijadwalkan ulang:</p>
          <ul className="mt-1 list-disc pl-5">
            {hasil.dipindah.map((t) => (
              <li key={t.id_task}>{t.nama_task}</li>
            ))}
          </ul>
        </div>
      )}

      {hasil.tidak_muat.length > 0 && (
        <div className={warningBoxClass}>
          <p className="font-medium">{hasil.tidak_muat.length} task tidak muat lagi minggu ini:</p>
          <ul className="mt-1 list-disc pl-5">
            {hasil.tidak_muat.map((t) => (
              <li key={t.id_task}>{t.nama_task}</li>
            ))}
          </ul>
        </div>
      )}

      {hasil.sesi_terlewat.length > 0 && (
        <div>
          <p className="text-sm font-medium">
            {hasil.sesi_terlewat.length} sesi terlewat belum dikonfirmasi. Apakah sempat kamu kerjakan?
          </p>
          <div className="mt-3 space-y-3">
            {hasil.sesi_terlewat.map((s) => {
              // GET /jadwal tidak memuat sesi `dilewati`: tidak ada di data terkini = sudah dilewati
              const terkini = sesiTerkini ? sesiTerkini.get(s.id_jadwal) ?? { ...s, status: "dilewati" as const } : s;
              return <SesiCard key={s.id_jadwal} sesi={terkini} sekarang={sekarang} tampilTanggal />;
            })}
          </div>
        </div>
      )}
    </div>
  );
}
