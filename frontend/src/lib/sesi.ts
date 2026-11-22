// Aturan aksi pada satu sesi jadwal (jadwal_task) — cermin PATCH /jadwal/sesi/{id} di backend,
// plus satu aturan tambahan di UI: sesi yang belum mulai tidak bisa ditandai selesai (backend tidak
// menolaknya, tapi label "selesai" untuk sesi yang belum terjadi akan mengotori dataset model).

import type { SesiRead } from "./api/types";
import { KONFIRMASI_BATAS_JAM, parseWib } from "./waktu";

export type AksiSesi = {
  /** Tombol Selesai / Tidak dikerjakan (status selesai | dilewati). */
  bisaKonfirmasi: boolean;
  /** Pindah waktu manual (hanya sesi terjadwal yang belum mulai). */
  bisaPindah: boolean;
  /** Kembalikan sesi selesai ke terjadwal. */
  bisaBatalSelesai: boolean;
  /** Sesi sudah mulai/terlewat tapi belum dikonfirmasi, masih dalam batas waktu → disorot. */
  perluKonfirmasi: boolean;
  /** Sedang berlangsung sekarang. */
  berlangsung: boolean;
  /** Batas konfirmasi (48 jam setelah selesai) sudah lewat. */
  lewatBatas: boolean;
};

export function aksiSesi(sesi: Pick<SesiRead, "status" | "waktu_mulai" | "waktu_selesai">, sekarang: Date): AksiSesi {
  const mulai = parseWib(sesi.waktu_mulai).getTime();
  const selesai = parseWib(sesi.waktu_selesai).getTime();
  const now = sekarang.getTime();
  const lewatBatas = now > selesai + KONFIRMASI_BATAS_JAM * 3600_000;
  const sudahMulai = now >= mulai;
  const berlangsung = sudahMulai && now < selesai;

  const kosong: AksiSesi = {
    bisaKonfirmasi: false,
    bisaPindah: false,
    bisaBatalSelesai: false,
    perluKonfirmasi: false,
    berlangsung,
    lewatBatas,
  };

  switch (sesi.status) {
    case "tidak_diketahui":
      // terlewat tanpa konfirmasi: hanya bisa dikonfirmasi, tidak bisa dipindah (409)
      return { ...kosong, bisaKonfirmasi: !lewatBatas, perluKonfirmasi: !lewatBatas };
    case "terjadwal":
      if (!sudahMulai) return { ...kosong, bisaPindah: true };
      return { ...kosong, bisaKonfirmasi: !lewatBatas, perluKonfirmasi: !lewatBatas };
    case "selesai":
      return { ...kosong, bisaBatalSelesai: !lewatBatas };
    default:
      // dilewati = riwayat, tidak bisa diubah
      return kosong;
  }
}

/** Sesi yang perlu dikonfirmasi user, urut waktu mulai. */
export function sesiPerluKonfirmasi<T extends Pick<SesiRead, "status" | "waktu_mulai" | "waktu_selesai">>(
  sesi: T[],
  sekarang: Date
): T[] {
  return sesi
    .filter((s) => aksiSesi(s, sekarang).perluKonfirmasi)
    .sort((a, b) => a.waktu_mulai.localeCompare(b.waktu_mulai));
}
