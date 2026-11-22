// Logika murni seputar rencana goal (tanpa React) — bisa diuji langsung.

import type { MilestoneRead, TimeConstraintRead } from "./api/types";
import { awalMinggu, hariDalamMinggu, jamKeMenit, tambahHari, tanggalDari } from "./waktu";

// Batas menit_harian di backend (goal_service.MENIT_HARIAN_MIN/MAKS, schema DecomposeRequest).
export const MENIT_HARIAN_MIN = 15;
export const MENIT_HARIAN_MAKS = 720;

// ---------------- pohon milestone ----------------

export type BulanRencana = {
  bulan: MilestoneRead;
  minggu: MilestoneRead[];
};

export type PohonRencana = {
  bulan: BulanRencana[];
  /** Milestone tanpa tipe bulanan/mingguan (format lama) atau yang induknya tidak ditemukan. */
  lainnya: MilestoneRead[];
};

/**
 * GoalDetail.milestones (daftar datar, urut pohon) → bulanan berisi mingguan.
 * Urutan dari backend dipertahankan.
 */
export function susunPohon(milestones: MilestoneRead[]): PohonRencana {
  const bulan: BulanRencana[] = [];
  const indeksBulan = new Map<number, BulanRencana>();

  for (const m of milestones) {
    if (m.tipe === "bulanan") {
      const item = { bulan: m, minggu: [] };
      bulan.push(item);
      indeksBulan.set(m.id_milestone, item);
    }
  }

  const lainnya: MilestoneRead[] = [];
  for (const m of milestones) {
    if (m.tipe === "bulanan") continue;
    const induk = m.id_parent_milestone != null ? indeksBulan.get(m.id_parent_milestone) : undefined;
    if (m.tipe === "mingguan" && induk) {
      induk.minggu.push(m);
    } else {
      lainnya.push(m);
    }
  }

  return { bulan, lainnya };
}

/**
 * Milestone mingguan yang minggunya (Senin–Minggu) memuat `tanggal` — sama dengan
 * goal_service.milestone_minggu: deadline mingguan (Minggu 23:59, atau deadline goal untuk minggu
 * terakhir) jatuh di minggu itu.
 */
export function mingguanPada(milestones: MilestoneRead[], tanggal: string): MilestoneRead | null {
  const senin = awalMinggu(tanggal);
  return (
    milestones.find(
      (m) => m.tipe === "mingguan" && m.deadline != null && awalMinggu(tanggalDari(m.deadline)) === senin
    ) ?? null
  );
}

export type StatusRinci = {
  /** Milestone mingguan minggu ini (null = goal belum direncanakan / di luar rentang goal). */
  ini: MilestoneRead | null;
  /** Minggu ini punya target tapi belum ada task → tawarkan "Rinci minggu ini". */
  iniPerluDirinci: boolean;
  /** Milestone mingguan minggu depan (null = minggu depan di luar rentang goal). */
  depan: MilestoneRead | null;
  /** Minggu depan sudah punya task. */
  depanSudahDirinci: boolean;
  /** Backend hanya mengizinkan rinci minggu depan mulai Sabtu (WIB). */
  depanBolehSekarang: boolean;
};

/** Status rincian task minggu ini & depan untuk tombol di halaman goal (D11). */
export function statusRinci(milestones: MilestoneRead[], hariIni: string): StatusRinci {
  const ini = mingguanPada(milestones, hariIni);
  const depan = mingguanPada(milestones, tambahHari(hariIni, 7));
  return {
    ini,
    iniPerluDirinci: ini !== null && ini.tasks.length === 0,
    depan,
    depanSudahDirinci: depan !== null && depan.tasks.length > 0,
    depanBolehSekarang: hariDalamMinggu(hariIni) >= 5,
  };
}

/** Jumlah task selesai / total dari semua milestone. */
export function progresTask(milestones: MilestoneRead[]): { selesai: number; total: number } {
  const tasks = milestones.flatMap((m) => m.tasks);
  return { selesai: tasks.filter((t) => t.status === "done").length, total: tasks.length };
}

/** Jumlah task (termasuk semua minggu) dalam satu daftar milestone. */
export function jumlahTask(milestones: MilestoneRead[]): number {
  return milestones.reduce((total, m) => total + m.tasks.length, 0);
}

// ---------------- estimasi waktu luang harian ----------------

const MENIT_SEHARI = 24 * 60;
const MENIT_SEMINGGU = 7 * MENIT_SEHARI;

type Rentang = [number, number]; // menit sejak Senin 00:00, [mulai, selesai)

function gabung(rentang: Rentang[]): Rentang[] {
  const urut = [...rentang].sort((a, b) => a[0] - b[0]);
  const hasil: Rentang[] = [];
  for (const [mulai, selesai] of urut) {
    const akhir = hasil[hasil.length - 1];
    if (akhir && mulai <= akhir[1]) {
      akhir[1] = Math.max(akhir[1], selesai);
    } else {
      hasil.push([mulai, selesai]);
    }
  }
  return hasil;
}

/** Durasi rentang mingguan; selesai <= mulai berarti melewati tengah malam (scheduler.WeeklyWindow). */
function durasiMenit(mulai: number, selesai: number): number {
  return selesai > mulai ? selesai - mulai : selesai + MENIT_SEHARI - mulai;
}

/**
 * Perkiraan menit luang per hari = rata-rata seminggu dari jam aktif dikurangi kegiatan rutin.
 * Cermin scheduler.average_daily_minutes (satu minggu Senin 00:00 – Senin berikutnya; kegiatan
 * Minggu malam yang lewat tengah malam ikut memotong Senin pagi). Hasil mentah, belum dibatasi
 * MENIT_HARIAN_MIN/MAKS.
 */
export function estimasiMenitHarian(
  kegiatanRutin: Pick<TimeConstraintRead, "hari_dalam_minggu" | "waktu_mulai" | "waktu_selesai">[],
  jamAktifMulai: string,
  jamAktifSelesai: string
): number {
  const aktifMulai = jamKeMenit(jamAktifMulai);
  const aktifDurasi = durasiMenit(aktifMulai, jamKeMenit(jamAktifSelesai));

  const potong = ([mulai, selesai]: Rentang): Rentang | null => {
    const a = Math.max(mulai, 0);
    const b = Math.min(selesai, MENIT_SEMINGGU);
    return a < b ? [a, b] : null;
  };

  const luang: Rentang[] = [];
  const sibuk: Rentang[] = [];
  // hari -1 = Minggu minggu sebelumnya (rentang lewat tengah malam ke Senin), sampai hari 7
  for (let hari = -1; hari <= 7; hari++) {
    const awalHari = hari * MENIT_SEHARI;
    const aktif = potong([awalHari + aktifMulai, awalHari + aktifMulai + aktifDurasi]);
    if (aktif) luang.push(aktif);

    const indeksHari = ((hari % 7) + 7) % 7;
    for (const k of kegiatanRutin) {
      if (k.hari_dalam_minggu !== indeksHari) continue;
      const mulai = jamKeMenit(k.waktu_mulai);
      const rentang = potong([awalHari + mulai, awalHari + mulai + durasiMenit(mulai, jamKeMenit(k.waktu_selesai))]);
      if (rentang) sibuk.push(rentang);
    }
  }

  // luang − sibuk
  const sibukGabung = gabung(sibuk);
  let total = 0;
  for (const [mulai, selesai] of gabung(luang)) {
    let kursor = mulai;
    for (const [sMulai, sSelesai] of sibukGabung) {
      if (sSelesai <= kursor || sMulai >= selesai) continue;
      if (sMulai > kursor) total += sMulai - kursor;
      kursor = Math.max(kursor, sSelesai);
      if (kursor >= selesai) break;
    }
    if (kursor < selesai) total += selesai - kursor;
  }

  return Math.floor(total / 7);
}
