// Geometri kalender mingguan (fungsi murni). Semua posisi dalam menit WIB, dihitung langsung dari
// string datetime WIB naive — tanpa Date, jadi tidak terpengaruh zona waktu browser.

import { jamDari, jamKeMenit, tanggalDari } from "./waktu";

const MENIT_SEHARI = 24 * 60;

/** Selisih hari kalender b − a ("YYYY-MM-DD"). */
export function selisihHari(a: string, b: string): number {
  const ke = (t: string) => {
    const [y, m, d] = t.split("-").map(Number);
    return Date.UTC(y, m - 1, d);
  };
  return Math.round((ke(b) - ke(a)) / 86_400_000);
}

/** Menit sejak Senin 00:00 minggu itu untuk datetime WIB naive. */
export function menitDariSenin(wib: string, senin: string): number {
  return selisihHari(senin, tanggalDari(wib)) * MENIT_SEHARI + jamKeMenit(jamDari(wib));
}

export type Segmen = {
  /** 0 = Senin … 6 = Minggu */
  hari: number;
  /** Menit dari awal area tampil (jam aktif mulai) */
  atas: number;
  tinggi: number;
  /** Bagian blok terpotong di atas/bawah area tampil (mulai lebih awal / selesai lebih larut). */
  terpotongAtas: boolean;
  terpotongBawah: boolean;
};

/**
 * Potong blok [mulai, selesai) menjadi segmen per hari yang terlihat di grid (jam tampil
 * `tampilMulai`–`tampilSelesai`, menit sejak 00:00). Blok yang melewati tengah malam dipecah;
 * bagian di luar jam tampil dibuang; hari di luar minggu (0–6) dibuang.
 */
export function segmenHarian(
  mulaiWib: string,
  selesaiWib: string,
  senin: string,
  tampilMulai: number,
  tampilSelesai: number
): Segmen[] {
  const mulai = menitDariSenin(mulaiWib, senin);
  const selesai = menitDariSenin(selesaiWib, senin);
  const hasil: Segmen[] = [];
  for (let hari = Math.floor(mulai / MENIT_SEHARI); hari * MENIT_SEHARI < selesai; hari++) {
    if (hari < 0 || hari > 6) continue;
    const awalHari = hari * MENIT_SEHARI;
    const a = Math.max(mulai, awalHari + tampilMulai);
    const b = Math.min(selesai, awalHari + tampilSelesai);
    if (a >= b) continue;
    hasil.push({
      hari,
      atas: a - awalHari - tampilMulai,
      tinggi: b - a,
      terpotongAtas: mulai < a,
      terpotongBawah: selesai > b,
    });
  }
  return hasil;
}

/**
 * Bagi blok yang tumpang tindih (dalam satu hari) ke lajur berdampingan. Mengembalikan
 * lajur ke-berapa tiap blok dan jumlah lajur di kelompok tumpang tindihnya.
 */
export function susunLajur(blok: { atas: number; tinggi: number }[]): { lajur: number; jumlahLajur: number }[] {
  const urutan = blok.map((b, i) => ({ ...b, i })).sort((x, y) => x.atas - y.atas || y.tinggi - x.tinggi);
  const hasil: { lajur: number; jumlahLajur: number }[] = blok.map(() => ({ lajur: 0, jumlahLajur: 1 }));

  let kelompok: typeof urutan = [];
  let akhirKelompok = -Infinity;
  let akhirLajur: number[] = [];

  const tutupKelompok = () => {
    const jumlah = akhirLajur.length || 1;
    for (const b of kelompok) hasil[b.i].jumlahLajur = jumlah;
    kelompok = [];
    akhirLajur = [];
  };

  for (const b of urutan) {
    if (b.atas >= akhirKelompok) tutupKelompok();
    let lajur = akhirLajur.findIndex((akhir) => akhir <= b.atas);
    if (lajur === -1) {
      lajur = akhirLajur.length;
      akhirLajur.push(0);
    }
    akhirLajur[lajur] = b.atas + b.tinggi;
    hasil[b.i].lajur = lajur;
    kelompok.push(b);
    akhirKelompok = Math.max(akhirKelompok, b.atas + b.tinggi);
  }
  tutupKelompok();
  return hasil;
}
