import type { SesiRead, TaskRingkas } from "../../lib/api/types";
import { formatRentangJam, formatTanggal, tanggalDari } from "../../lib/waktu";
import { infoBoxClass, warningBoxClass } from "../ui";

/** Ringkasan hasil POST /jadwal/goal/{id}: sesi baru per hari + task yang tidak muat. */
export default function HasilPenjadwalan({
  sesiBaru,
  tidakMuat,
}: {
  sesiBaru: SesiRead[];
  tidakMuat: TaskRingkas[];
}) {
  const perHari = new Map<string, SesiRead[]>();
  for (const sesi of [...sesiBaru].sort((a, b) => a.waktu_mulai.localeCompare(b.waktu_mulai))) {
    const tanggal = tanggalDari(sesi.waktu_mulai);
    perHari.set(tanggal, [...(perHari.get(tanggal) ?? []), sesi]);
  }

  return (
    <div className="space-y-4">
      {sesiBaru.length === 0 && tidakMuat.length === 0 && (
        <p className={infoBoxClass}>Semua task minggu ini sudah terjadwal. Tidak ada sesi baru.</p>
      )}

      {sesiBaru.length > 0 && (
        <div>
          <p className="text-sm font-semibold">{sesiBaru.length} sesi baru dijadwalkan</p>
          <div className="mt-3 space-y-3">
            {[...perHari.entries()].map(([tanggal, sesi]) => (
              <div key={tanggal} className="rounded-lg border border-[#EBE2D6] bg-white p-4">
                <p className="text-xs font-semibold uppercase tracking-wide text-[#8B857B]">
                  {formatTanggal(tanggal, { weekday: "long", day: "numeric", month: "long" })}
                </p>
                <ul className="mt-2 space-y-1.5">
                  {sesi.map((s) => (
                    <li key={s.id_jadwal} className="flex gap-3 text-sm">
                      <span className="w-24 shrink-0 tabular-nums text-[#8B857B]">
                        {formatRentangJam(s.waktu_mulai, s.waktu_selesai)}
                      </span>
                      <span>{s.nama_task}</span>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      )}

      {tidakMuat.length > 0 && (
        <div className={warningBoxClass}>
          <p className="font-medium">{tidakMuat.length} task tidak muat di sisa minggu ini:</p>
          <ul className="mt-1 list-disc pl-5">
            {tidakMuat.map((t) => (
              <li key={t.id_task}>{t.nama_task}</li>
            ))}
          </ul>
          <p className="mt-2">
            Kurangi kegiatan rutin atau agenda, atau coba jadwalkan lagi setelah ada slot kosong.
          </p>
        </div>
      )}
    </div>
  );
}
