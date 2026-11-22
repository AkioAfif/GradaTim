"use client";

import { useMemo, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { CalendarPlus, ChevronLeft, ChevronRight, RefreshCw, Trash2 } from "lucide-react";

import DashboardLayout from "../../components/DashboardLayout";
import UserAvatar from "../../components/UserAvatar";
import AgendaModal from "../../components/jadwal/AgendaModal";
import HasilSusunUlang from "../../components/jadwal/HasilSusunUlang";
import KotakPerluKonfirmasi from "../../components/jadwal/KotakPerluKonfirmasi";
import SesiCard, { gayaSesi } from "../../components/jadwal/SesiCard";
import { useSekarang, useSusunUlang } from "../../components/jadwal/hooks";
import { cardClass, errorBoxClass, secondaryButtonClass } from "../../components/ui";
import { deleteAgenda } from "../../lib/api/agenda";
import { toApiError, type ApiError } from "../../lib/api/client";
import { invalidateJadwal, useAgenda, useJadwalMinggu } from "../../lib/api/queries";
import type { AgendaRead, BlokKalender, JadwalMingguan, SesiRead } from "../../lib/api/types";
import { segmenHarian, susunLajur } from "../../lib/kalender";
import { sesiPerluKonfirmasi } from "../../lib/sesi";
import {
  NAMA_HARI_PENDEK,
  awalMinggu,
  formatRentangJam,
  formatTanggal,
  hariIniWib,
  hariSeminggu,
  jamKeMenit,
  tambahHari,
  tanggalDari,
} from "../../lib/waktu";

const PX_PER_MENIT = 0.8;
const TINGGI_MIN_BLOK = 18;

type BlokGrid =
  | { jenis: "rutin"; data: BlokKalender }
  | { jenis: "agenda"; data: BlokKalender }
  | { jenis: "sesi"; data: SesiRead };

type BlokTampil = {
  key: string;
  blok: BlokGrid;
  hari: number;
  atas: number;
  tinggi: number;
  lajur: number;
  jumlahLajur: number;
};

/** Semua blok minggu itu → posisi per hari (rutin di belakang selebar kolom; agenda & sesi berlajur). */
function susunBlok(jadwal: JadwalMingguan, senin: string, tampilMulai: number, tampilSelesai: number) {
  const blok: BlokGrid[] = [
    ...jadwal.kegiatan_rutin.map((data) => ({ jenis: "rutin" as const, data })),
    ...jadwal.agenda.map((data) => ({ jenis: "agenda" as const, data })),
    ...jadwal.sesi.map((data) => ({ jenis: "sesi" as const, data })),
  ];

  const segmen = blok.flatMap((b, i) =>
    segmenHarian(b.data.waktu_mulai, b.data.waktu_selesai, senin, tampilMulai, tampilSelesai).map((s, j) => ({
      key: `${b.jenis}-${b.jenis === "sesi" ? b.data.id_jadwal : i}-${j}`,
      blok: b,
      ...s,
    }))
  );

  const hasil: BlokTampil[] = [];
  for (let hari = 0; hari < 7; hari++) {
    const rutin = segmen.filter((s) => s.hari === hari && s.blok.jenis === "rutin");
    hasil.push(...rutin.map((s) => ({ ...s, lajur: 0, jumlahLajur: 1 })));
    const atas = segmen.filter((s) => s.hari === hari && s.blok.jenis !== "rutin");
    const lajur = susunLajur(atas);
    hasil.push(...atas.map((s, i) => ({ ...s, ...lajur[i] })));
  }
  return hasil;
}

function GridMinggu({
  jadwal,
  senin,
  hariIni,
  hariDipilih,
  onPilihHari,
  sekarang,
}: {
  jadwal: JadwalMingguan;
  senin: string;
  hariIni: string;
  hariDipilih: string;
  onPilihHari: (tanggal: string) => void;
  sekarang: Date;
}) {
  const tampilMulai = jamKeMenit(jadwal.jam_aktif_mulai);
  const tampilSelesai = jamKeMenit(jadwal.jam_aktif_selesai);
  const tinggi = (tampilSelesai - tampilMulai) * PX_PER_MENIT;
  const hari = hariSeminggu(senin);
  const blok = useMemo(
    () => susunBlok(jadwal, senin, tampilMulai, tampilSelesai),
    [jadwal, senin, tampilMulai, tampilSelesai]
  );
  const jamLabel: number[] = [];
  for (let m = Math.ceil(tampilMulai / 60) * 60; m <= tampilSelesai; m += 60) jamLabel.push(m);

  return (
    <div className="overflow-x-auto">
      <div className="min-w-[720px] pb-3">
        {/* kepala hari */}
        <div className="grid grid-cols-[48px_repeat(7,1fr)] border-b border-[#E9E0D4] pb-2">
          <div />
          {hari.map((tanggal, i) => (
            <button
              key={tanggal}
              type="button"
              onClick={() => onPilihHari(tanggal)}
              className={`mx-0.5 rounded-lg py-1.5 text-center text-xs ${
                tanggal === hariDipilih
                  ? "bg-[#826049] text-white"
                  : tanggal === hariIni
                    ? "bg-[#EFF2EB] font-semibold text-[#506851]"
                    : "hover:bg-[#F3EADD]"
              }`}
            >
              <span className="block">{NAMA_HARI_PENDEK[i]}</span>
              <span className="block text-sm font-medium">{Number(tanggal.slice(8))}</span>
            </button>
          ))}
        </div>

        {/* badan grid */}
        <div className="relative grid grid-cols-[48px_repeat(7,1fr)]" style={{ height: tinggi }}>
          <div className="relative">
            {jamLabel.map((m) => (
              <span
                key={m}
                className="absolute right-2 -translate-y-1/2 text-[10px] text-[#A49A8C]"
                style={{ top: (m - tampilMulai) * PX_PER_MENIT }}
              >
                {String(m / 60).padStart(2, "0")}.00
              </span>
            ))}
          </div>

          {hari.map((tanggal, indeksHari) => (
            <div
              key={tanggal}
              className={`relative border-l border-[#EFE7DC] ${tanggal === hariIni ? "bg-[#F7FAF4]" : ""}`}
              onClick={() => onPilihHari(tanggal)}
            >
              {jamLabel.map((m) => (
                <div
                  key={m}
                  className="absolute inset-x-0 border-t border-dashed border-[#F0E9DF]"
                  style={{ top: (m - tampilMulai) * PX_PER_MENIT }}
                />
              ))}

              {blok
                .filter((b) => b.hari === indeksHari)
                .map((b) => {
                  const style = {
                    top: b.atas * PX_PER_MENIT,
                    height: Math.max(b.tinggi * PX_PER_MENIT, TINGGI_MIN_BLOK),
                    left: `calc(${(b.lajur / b.jumlahLajur) * 100}% + 2px)`,
                    width: `calc(${100 / b.jumlahLajur}% - 4px)`,
                  };
                  const rentang = formatRentangJam(b.blok.data.waktu_mulai, b.blok.data.waktu_selesai);
                  if (b.blok.jenis === "rutin") {
                    return (
                      <div
                        key={b.key}
                        title={`${b.blok.data.nama} (${rentang})`}
                        style={style}
                        className="absolute overflow-hidden rounded-md bg-[repeating-linear-gradient(135deg,#ECE9E1_0_6px,#E4E0D6_6px_12px)] px-1.5 py-0.5 text-[10px] text-[#7A776E]"
                      >
                        {b.blok.data.nama}
                      </div>
                    );
                  }
                  if (b.blok.jenis === "agenda") {
                    return (
                      <div
                        key={b.key}
                        title={`Agenda: ${b.blok.data.nama} (${rentang})`}
                        style={style}
                        className="absolute z-10 overflow-hidden rounded-md border border-[#D7A27E] bg-[#F8E4D3] px-1.5 py-0.5 text-[10px] text-[#6D4D38]"
                      >
                        {b.blok.data.nama}
                      </div>
                    );
                  }
                  const sesi = b.blok.data;
                  return (
                    <button
                      key={b.key}
                      type="button"
                      onClick={(event) => {
                        event.stopPropagation();
                        onPilihHari(tanggalDari(sesi.waktu_mulai));
                      }}
                      title={`${sesi.nama_task} (${rentang})`}
                      aria-label={`${sesi.nama_task}, ${rentang}`}
                      style={style}
                      className={`absolute z-20 overflow-hidden rounded-md border px-1.5 py-0.5 text-left text-[10px] leading-tight ${gayaSesi(sesi, sekarang)}`}
                    >
                      <span className="block truncate font-medium">{sesi.nama_task}</span>
                      <span className="block truncate opacity-80">{rentang}</span>
                    </button>
                  );
                })}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function Legenda() {
  const item = [
    ["bg-[#F1F5EE] border-[#B9C7B1]", "Terjadwal"],
    ["bg-[#FBF0DC] border-[#D9A441]", "Perlu konfirmasi"],
    ["bg-[#DCE7D5] border-[#82947B]", "Selesai"],
    ["bg-[#F8E4D3] border-[#D7A27E]", "Agenda"],
    ["bg-[#ECE9E1] border-[#E4E0D6]", "Kegiatan rutin"],
  ];
  return (
    <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-[#8B857B]">
      {item.map(([kelas, label]) => (
        <span key={label} className="inline-flex items-center gap-1.5">
          <span className={`inline-block h-3 w-3 rounded-sm border ${kelas}`} />
          {label}
        </span>
      ))}
    </div>
  );
}

function DetailHari({
  tanggal,
  jadwal,
  agenda,
  sekarang,
}: {
  tanggal: string;
  jadwal: JadwalMingguan;
  agenda: AgendaRead[];
  sekarang: Date;
}) {
  const queryClient = useQueryClient();
  const hapus = useMutation<void, ApiError, number>({
    mutationFn: async (idAgenda) => {
      try {
        await deleteAgenda(idAgenda);
      } catch (err) {
        throw toApiError(err);
      }
    },
    onSuccess: () => invalidateJadwal(queryClient),
  });

  const sesi = jadwal.sesi
    .filter((s) => tanggalDari(s.waktu_mulai) === tanggal)
    .sort((a, b) => a.waktu_mulai.localeCompare(b.waktu_mulai));
  const agendaHari = agenda
    .filter((a) => tanggalDari(a.waktu_mulai) === tanggal)
    .sort((a, b) => a.waktu_mulai.localeCompare(b.waktu_mulai));
  // rutin yang beririsan dengan tanggal ini (termasuk yang mulai kemarin malam)
  const rutin = jadwal.kegiatan_rutin.filter(
    (r) => tanggalDari(r.waktu_mulai) === tanggal || tanggalDari(r.waktu_selesai) === tanggal
  );

  return (
    <div className="space-y-6">
      <h2 className="text-base font-semibold">{formatTanggal(tanggal)}</h2>

      <div>
        <p className="text-xs font-semibold uppercase tracking-wide text-[#8B857B]">Sesi task</p>
        {sesi.length === 0 ? (
          <p className="mt-2 text-sm text-[#8B857B]">Tidak ada sesi.</p>
        ) : (
          <div className="mt-2 space-y-3">
            {sesi.map((s) => (
              <SesiCard key={s.id_jadwal} sesi={s} sekarang={sekarang} />
            ))}
          </div>
        )}
      </div>

      <div>
        <p className="text-xs font-semibold uppercase tracking-wide text-[#8B857B]">Agenda</p>
        {agendaHari.length === 0 ? (
          <p className="mt-2 text-sm text-[#8B857B]">Tidak ada agenda.</p>
        ) : (
          <ul className="mt-2 divide-y divide-[#EBE2D6] rounded-lg border border-[#EBE2D6] bg-white">
            {agendaHari.map((a) => (
              <li key={a.id_agenda} className="flex items-center justify-between gap-3 px-4 py-3 text-sm">
                <span>
                  <span className="font-medium">{a.nama}</span>{" "}
                  <span className="text-[#8B857B]">{formatRentangJam(a.waktu_mulai, a.waktu_selesai)}</span>
                </span>
                <button
                  type="button"
                  disabled={hapus.isPending}
                  onClick={() => window.confirm(`Hapus agenda "${a.nama}"?`) && hapus.mutate(a.id_agenda)}
                  aria-label={`Hapus agenda ${a.nama}`}
                  title="Hapus"
                  className="rounded-md p-1.5 text-[#A24A3A] hover:bg-[#F8E1DA] disabled:opacity-50"
                >
                  <Trash2 size={16} />
                </button>
              </li>
            ))}
          </ul>
        )}
        {hapus.isError && <p className="mt-2 text-xs text-[#8A3B2E]">{hapus.error.message}</p>}
      </div>

      {rutin.length > 0 && (
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-[#8B857B]">Kegiatan rutin</p>
          <ul className="mt-2 space-y-1 text-sm text-[#64675E]">
            {rutin.map((r, i) => (
              <li key={i}>
                {r.nama} <span className="text-[#8B857B]">{formatRentangJam(r.waktu_mulai, r.waktu_selesai)}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

export default function CalendarPage() {
  const hariIni = hariIniWib();
  const sekarang = useSekarang();
  const [senin, setSenin] = useState(() => awalMinggu(hariIni));
  const [hariDipilih, setHariDipilih] = useState(hariIni);
  const [tambahAgenda, setTambahAgenda] = useState(false);

  const minggu = tambahHari(senin, 6);
  const jadwal = useJadwalMinggu(senin);
  const agenda = useAgenda(senin, minggu);
  const susunUlang = useSusunUlang();
  const mingguIni = senin === awalMinggu(hariIni);

  function gantiMinggu(seninBaru: string) {
    setSenin(seninBaru);
    setHariDipilih(awalMinggu(hariIni) === seninBaru ? hariIni : seninBaru);
    susunUlang.reset(); // hasil susun ulang hanya berlaku untuk minggu ini
  }

  const perluKonfirmasi = jadwal.data ? sesiPerluKonfirmasi(jadwal.data.sesi, sekarang) : [];
  const sesiTerkini = useMemo(
    () => new Map((jadwal.data?.sesi ?? []).map((s) => [s.id_jadwal, s])),
    [jadwal.data]
  );

  return (
    <DashboardLayout>
      <div className="mx-auto max-w-6xl">
        <header className="flex items-center justify-between border-b border-[#E9E0D4] pb-5">
          <p className="text-xs text-[#8B857B]">Kalender</p>
          <UserAvatar />
        </header>

        <section className="mt-7 flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="text-3xl font-medium tracking-tight md:text-4xl">Kalender Mingguan</h1>
            <p className="mt-2 text-sm text-[#8B857B]">
              {formatTanggal(senin, { day: "numeric", month: "long" })} –{" "}
              {formatTanggal(minggu, { day: "numeric", month: "long", year: "numeric" })}
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={() => gantiMinggu(tambahHari(senin, -7))}
              aria-label="Minggu sebelumnya"
              className="rounded-lg border border-[#DDD2C3] bg-white p-2.5 hover:bg-[#F3EADD]"
            >
              <ChevronLeft size={18} />
            </button>
            <button
              type="button"
              disabled={mingguIni}
              onClick={() => gantiMinggu(awalMinggu(hariIni))}
              className="rounded-lg border border-[#DDD2C3] bg-white px-3.5 py-2.5 text-sm hover:bg-[#F3EADD] disabled:opacity-50"
            >
              Minggu ini
            </button>
            <button
              type="button"
              onClick={() => gantiMinggu(tambahHari(senin, 7))}
              aria-label="Minggu berikutnya"
              className="rounded-lg border border-[#DDD2C3] bg-white p-2.5 hover:bg-[#F3EADD]"
            >
              <ChevronRight size={18} />
            </button>
            <button
              type="button"
              onClick={() => setTambahAgenda(true)}
              className={`inline-flex items-center gap-2 ${secondaryButtonClass} py-2.5`}
            >
              <CalendarPlus size={16} /> Agenda
            </button>
            {mingguIni && (
              <button
                type="button"
                disabled={susunUlang.isPending}
                onClick={() => susunUlang.mutate()}
                title="Jadwalkan ulang sesi yang terlewat ke slot kosong minggu ini"
                className={`inline-flex items-center gap-2 ${secondaryButtonClass} py-2.5`}
              >
                <RefreshCw size={16} className={susunUlang.isPending ? "animate-spin" : ""} /> Susun ulang
              </button>
            )}
          </div>
        </section>

        {susunUlang.isError && (
          <p role="alert" className={`mt-5 ${errorBoxClass}`}>
            {susunUlang.error.message}
          </p>
        )}
        {susunUlang.isSuccess && mingguIni && (
          <section className={`mt-5 ${cardClass}`}>
            <div className="mb-4 flex items-center justify-between gap-3">
              <h2 className="text-base font-semibold">Hasil susun ulang</h2>
              <button type="button" onClick={() => susunUlang.reset()} className="text-xs underline">
                Tutup
              </button>
            </div>
            <HasilSusunUlang hasil={susunUlang.data} sekarang={sekarang} sesiTerkini={sesiTerkini} />
          </section>
        )}

        {perluKonfirmasi.length > 0 && (
          <div className="mt-5">
            <KotakPerluKonfirmasi sesi={perluKonfirmasi} sekarang={sekarang} />
          </div>
        )}

        {jadwal.isPending ? (
          <p className="mt-7 text-sm text-[#8B857B]">Memuat kalender...</p>
        ) : jadwal.isError ? (
          <p role="alert" className={`mt-7 ${errorBoxClass}`}>
            {jadwal.error.message}
          </p>
        ) : (
          <div className="mt-6 grid gap-6 xl:grid-cols-[1fr_360px]">
            {/* min-w-0: item grid boleh menyempit sehingga grid jam bisa digeser di dalam kartu */}
            <section className={`min-w-0 ${cardClass}`}>
              <GridMinggu
                jadwal={jadwal.data}
                senin={senin}
                hariIni={hariIni}
                hariDipilih={hariDipilih}
                onPilihHari={setHariDipilih}
                sekarang={sekarang}
              />
              <Legenda />
            </section>

            <section className={`min-w-0 ${cardClass}`}>
              <DetailHari tanggal={hariDipilih} jadwal={jadwal.data} agenda={agenda.data ?? []} sekarang={sekarang} />
            </section>
          </div>
        )}

        {tambahAgenda && <AgendaModal tanggalAwal={hariDipilih} onTutup={() => setTambahAgenda(false)} />}
      </div>
    </DashboardLayout>
  );
}
