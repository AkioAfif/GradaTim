"use client";

import { useState } from "react";
import Link from "next/link";
import { Check, MoveRight, Undo2, X } from "lucide-react";

import type { SesiRead } from "../../lib/api/types";
import { LABEL_STATUS_SESI } from "../../lib/label";
import { aksiSesi } from "../../lib/sesi";
import { formatRentangJam, formatTanggal } from "../../lib/waktu";
import { useUbahSesi } from "./hooks";
import PindahSesiModal from "./PindahSesiModal";

/** Warna kartu/blok per keadaan sesi (dipakai juga oleh grid kalender). */
export function gayaSesi(sesi: SesiRead, sekarang: Date): string {
  const aksi = aksiSesi(sesi, sekarang);
  if (sesi.status === "selesai") return "border-[#82947B] bg-[#DCE7D5] text-[#3E5340]";
  // dilewati, atau terlewat tanpa konfirmasi sampai batas 48 jam habis → redup
  if (sesi.status === "dilewati" || aksi.lewatBatas) {
    return "border-[#D8CFC3] bg-[#F1ECE4] text-[#8B857B]";
  }
  if (aksi.perluKonfirmasi && !aksi.berlangsung) return "border-[#D9A441] bg-[#FBF0DC] text-[#6B4E12]";
  if (aksi.berlangsung) return "border-[#506851] bg-[#E8EFE4] text-[#30312B] ring-1 ring-[#506851]";
  return "border-[#B9C7B1] bg-[#F1F5EE] text-[#30312B]";
}

function labelKeadaan(sesi: SesiRead, sekarang: Date): string {
  const aksi = aksiSesi(sesi, sekarang);
  if (aksi.berlangsung && sesi.status === "terjadwal") return "Sedang berlangsung";
  if (sesi.status === "terjadwal" && aksi.perluKonfirmasi) return "Perlu konfirmasi";
  if (aksi.lewatBatas && (sesi.status === "terjadwal" || sesi.status === "tidak_diketahui")) {
    return "Tidak dikonfirmasi";
  }
  return LABEL_STATUS_SESI[sesi.status];
}

/**
 * Satu sesi beserta tombol konfirmasinya. Konfirmasi Selesai / Tidak dikerjakan adalah label data
 * model personalisasi (docs/AI.md §2), jadi tombolnya dibuat menonjol.
 */
export default function SesiCard({
  sesi,
  sekarang,
  tampilTanggal = false,
}: {
  sesi: SesiRead;
  sekarang: Date;
  tampilTanggal?: boolean;
}) {
  const ubah = useUbahSesi();
  const [pindah, setPindah] = useState(false);
  const aksi = aksiSesi(sesi, sekarang);

  function konfirmasi(status: "selesai" | "dilewati" | "terjadwal") {
    if (
      status === "dilewati" &&
      !window.confirm("Tandai sesi ini tidak dikerjakan? Status ini tidak bisa diubah lagi.")
    ) {
      return;
    }
    ubah.mutate({ idJadwal: sesi.id_jadwal, perubahan: { status } });
  }

  return (
    <div className={`rounded-lg border p-4 ${gayaSesi(sesi, sekarang)}`}>
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0">
          <p className={`text-sm font-medium ${sesi.status === "selesai" ? "line-through decoration-1" : ""}`}>
            {sesi.nama_task}
          </p>
          <p className="mt-0.5 text-xs opacity-80">
            {tampilTanggal && `${formatTanggal(sesi.waktu_mulai, { weekday: "short", day: "numeric", month: "short" })} · `}
            {formatRentangJam(sesi.waktu_mulai, sesi.waktu_selesai)}
            {sesi.dipindah && " · dipindah"}
          </p>
        </div>
        <span className="shrink-0 rounded-full bg-white/70 px-2.5 py-0.5 text-xs font-medium">
          {labelKeadaan(sesi, sekarang)}
        </span>
      </div>

      {(aksi.bisaKonfirmasi || aksi.bisaBatalSelesai || aksi.bisaPindah) && (
        <div className="mt-3 flex flex-wrap gap-2">
          {aksi.bisaKonfirmasi && (
            <>
              <button
                type="button"
                disabled={ubah.isPending}
                onClick={() => konfirmasi("selesai")}
                className="inline-flex items-center gap-1.5 rounded-lg bg-[#506851] px-3.5 py-2 text-xs font-medium text-white hover:bg-[#3E5340] disabled:opacity-60"
              >
                <Check size={14} /> Selesai
              </button>
              <button
                type="button"
                disabled={ubah.isPending}
                onClick={() => konfirmasi("dilewati")}
                className="inline-flex items-center gap-1.5 rounded-lg border border-[#C9BBA9] bg-white px-3.5 py-2 text-xs font-medium hover:bg-[#F4F0E7] disabled:opacity-60"
              >
                <X size={14} /> Tidak dikerjakan
              </button>
            </>
          )}
          {aksi.bisaBatalSelesai && (
            <button
              type="button"
              disabled={ubah.isPending}
              onClick={() => konfirmasi("terjadwal")}
              className="inline-flex items-center gap-1.5 rounded-lg border border-[#B9C7B1] bg-white/70 px-3 py-1.5 text-xs hover:bg-white disabled:opacity-60"
            >
              <Undo2 size={13} /> Batalkan selesai
            </button>
          )}
          {aksi.bisaPindah && (
            <button
              type="button"
              disabled={ubah.isPending}
              onClick={() => setPindah(true)}
              className="inline-flex items-center gap-1.5 rounded-lg border border-[#B9C7B1] bg-white/70 px-3 py-1.5 text-xs hover:bg-white disabled:opacity-60"
            >
              <MoveRight size={13} /> Pindah
            </button>
          )}
        </div>
      )}

      {ubah.isError && !pindah && (
        <p role="alert" className="mt-2 text-xs text-[#8A3B2E]">
          {ubah.error.message}
        </p>
      )}

      <Link href={`/goals/${sesi.id_goal}`} className="mt-2 inline-block text-xs underline opacity-70 hover:opacity-100">
        Lihat goal
      </Link>

      {pindah && <PindahSesiModal sesi={sesi} onTutup={() => setPindah(false)} />}
    </div>
  );
}
