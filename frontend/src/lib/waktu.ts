// Helper waktu — satu-satunya tempat logika zona waktu di frontend.
//
// Backend menyimpan & mengirim datetime sebagai WIB TANPA zona waktu ("2026-11-23T09:00:00").
// `new Date("2026-11-23T09:00:00")` akan membacanya sebagai jam LOKAL browser, dan
// `date.toISOString()` mengubahnya ke UTC — keduanya menggeser jam bila browser bukan WIB.
// Karena itu:
//   - string WIB → instant: parseWib() (menempelkan offset +07:00)
//   - instant → string WIB: keWibNaive()
//   - tampilan: format*() selalu memakai zona Asia/Jakarta
//   - tanggal ("YYYY-MM-DD") dihitung sebagai tanggal WIB, dengan aritmetika UTC agar bebas DST.
// Hasilnya benar apa pun zona waktu komputer user.

const WIB_OFFSET_MS = 7 * 60 * 60 * 1000;
export const ZONA_WIB = "Asia/Jakarta";

/** Batas konfirmasi status sesi setelah sesi berakhir (cermin KONFIRMASI_BATAS_JAM backend). */
export const KONFIRMASI_BATAS_JAM = 48;

function pad(n: number): string {
  return String(n).padStart(2, "0");
}

/** String datetime WIB naive dari API → Date (instant). String yang sudah ber-offset dihormati. */
export function parseWib(value: string): Date {
  const punyaZona = /(Z|[+-]\d{2}:?\d{2})$/.test(value);
  return new Date(punyaZona ? value : `${value}+07:00`);
}

/** Date (instant) → "YYYY-MM-DDTHH:mm:ss" WIB naive, format yang diterima backend. */
export function keWibNaive(date: Date): string {
  const w = new Date(date.getTime() + WIB_OFFSET_MS);
  return (
    `${w.getUTCFullYear()}-${pad(w.getUTCMonth() + 1)}-${pad(w.getUTCDate())}` +
    `T${pad(w.getUTCHours())}:${pad(w.getUTCMinutes())}:${pad(w.getUTCSeconds())}`
  );
}

/** Gabungkan tanggal "YYYY-MM-DD" + jam "HH:mm" (dari <input>) → datetime WIB naive. */
export function gabungTanggalJam(tanggal: string, jam: string): string {
  return `${tanggal}T${jam.slice(0, 5)}:00`;
}

/** Tanggal WIB ("YYYY-MM-DD") dari sebuah instant; default sekarang. */
export function tanggalWib(date: Date = new Date()): string {
  return keWibNaive(date).slice(0, 10);
}

export function hariIniWib(): string {
  return tanggalWib(new Date());
}

/** Bagian tanggal dari datetime WIB naive ("2026-11-23T09:00:00" → "2026-11-23"). */
export function tanggalDari(wib: string): string {
  return wib.slice(0, 10);
}

/** Bagian jam "HH:mm" dari datetime WIB naive atau jam "HH:MM:SS". */
export function jamDari(value: string): string {
  const jam = value.includes("T") ? value.split("T")[1] : value;
  return jam.slice(0, 5);
}

/** "HH:MM[:SS]" → menit sejak 00:00. */
export function jamKeMenit(jam: string): number {
  const [h, m] = jam.split(":").map(Number);
  return h * 60 + m;
}

// ---------------- aritmetika tanggal (string "YYYY-MM-DD") ----------------

function tanggalKeUtc(tanggal: string): Date {
  const [y, m, d] = tanggal.split("-").map(Number);
  return new Date(Date.UTC(y, m - 1, d));
}

function utcKeTanggal(date: Date): string {
  return `${date.getUTCFullYear()}-${pad(date.getUTCMonth() + 1)}-${pad(date.getUTCDate())}`;
}

export function tambahHari(tanggal: string, hari: number): string {
  const d = tanggalKeUtc(tanggal);
  d.setUTCDate(d.getUTCDate() + hari);
  return utcKeTanggal(d);
}

/** 0 = Senin … 6 = Minggu (sama dengan hari_dalam_minggu di backend). */
export function hariDalamMinggu(tanggal: string): number {
  return (tanggalKeUtc(tanggal).getUTCDay() + 6) % 7;
}

/** Tanggal Senin dari minggu yang memuat `tanggal`. */
export function awalMinggu(tanggal: string): string {
  return tambahHari(tanggal, -hariDalamMinggu(tanggal));
}

/** 7 tanggal Senin–Minggu dari minggu yang memuat `tanggal`. */
export function hariSeminggu(tanggal: string): string[] {
  const senin = awalMinggu(tanggal);
  return Array.from({ length: 7 }, (_, i) => tambahHari(senin, i));
}

/** Sabtu atau Minggu (WIB) — syarat rinci task minggu depan. */
export function akhirPekanWib(): boolean {
  return hariDalamMinggu(hariIniWib()) >= 5;
}

// ---------------- format tampilan (bahasa Indonesia, zona WIB) ----------------

export const NAMA_HARI = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"];
export const NAMA_HARI_PENDEK = ["Sen", "Sel", "Rab", "Kam", "Jum", "Sab", "Min"];

/** "09.00" dari datetime WIB naive. */
export function formatJam(wib: string): string {
  return jamDari(wib).replace(":", ".");
}

/** "09.00–10.30". */
export function formatRentangJam(mulai: string, selesai: string): string {
  return `${formatJam(mulai)}–${formatJam(selesai)}`;
}

/** Tanggal ("YYYY-MM-DD" atau datetime WIB naive) → mis. "Senin, 23 November 2026". */
export function formatTanggal(
  value: string,
  options: Intl.DateTimeFormatOptions = { weekday: "long", day: "numeric", month: "long", year: "numeric" }
): string {
  // Tengah hari WIB: aman dari pergeseran tanggal apa pun zona tampilannya.
  const instant = parseWib(`${tanggalDari(value)}T12:00:00`);
  return instant.toLocaleDateString("id-ID", { ...options, timeZone: ZONA_WIB });
}

/** "23 Nov" — ringkas untuk label kalender. */
export function formatTanggalPendek(value: string): string {
  return formatTanggal(value, { day: "numeric", month: "short" });
}

/** Durasi menit → "1 jam 30 menit". */
export function formatDurasi(menit: number | null | undefined): string {
  if (menit == null) return "—";
  const jam = Math.floor(menit / 60);
  const sisa = menit % 60;
  if (jam === 0) return `${sisa} menit`;
  return sisa === 0 ? `${jam} jam` : `${jam} jam ${sisa} menit`;
}
