// Aturan aksi pada satu sesi jadwal (jadwal_task) — cermin PATCH /jadwal/sesi/{id} di backend,
// termasuk: sesi yang belum mulai tidak bisa ditandai selesai/dilewati (backend menjawab 409, karena
// label untuk sesi yang belum terjadi akan mengotori dataset model).

import type { SesiRead } from "./api/types";
import { KONFIRMASI_BATAS_JAM, parseWib, tanggalDari } from "./waktu";

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

type SesiWaktu = Pick<SesiRead, "status" | "waktu_mulai" | "waktu_selesai">;

/** Sesi pada tanggal tertentu (menurut waktu mulai), urut waktu mulai. */
export function sesiPadaTanggal<T extends SesiWaktu>(sesi: T[], tanggal: string): T[] {
  return sesi
    .filter((s) => tanggalDari(s.waktu_mulai) === tanggal)
    .sort((a, b) => a.waktu_mulai.localeCompare(b.waktu_mulai));
}

/**
 * Sesi terjadwal pertama hari ini yang belum mulai. Mood sebaiknya diisi sebelum sesi ini:
 * mood yang diisi setelah sesi mulai tidak dipakai sebagai fitur sesi itu (docs/AI.md §2).
 */
export function sesiBerikutnyaHariIni<T extends SesiWaktu>(sesi: T[], tanggal: string, sekarang: Date): T | null {
  return (
    sesiPadaTanggal(sesi, tanggal).find(
      (s) => s.status === "terjadwal" && parseWib(s.waktu_mulai).getTime() > sekarang.getTime()
    ) ?? null
  );
}

export type RingkasanHari = { tanggal: string; total: number; selesai: number };

/** Jumlah sesi & sesi selesai per hari untuk 7 tanggal yang diberikan. */
export function ringkasanPerHari(sesi: SesiWaktu[], tanggal: string[]): RingkasanHari[] {
  return tanggal.map((t) => {
    const hari = sesi.filter((s) => tanggalDari(s.waktu_mulai) === t);
    return { tanggal: t, total: hari.length, selesai: hari.filter((s) => s.status === "selesai").length };
  });
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
