"use client";

import { useState, type FormEvent } from "react";

import Modal from "../Modal";
import { errorBoxClass, fieldErrorClass, inputClass, labelClass, primaryButtonClass, secondaryButtonClass } from "../ui";
import type { Bentrok } from "../../lib/api/client";
import type { SesiRead } from "../../lib/api/types";
import { gabungTanggalJam, formatRentangJam, formatTanggal, jamDari, jamKeMenit, parseWib, tanggalDari } from "../../lib/waktu";
import { useUbahSesi } from "./hooks";

const LABEL_JENIS: Record<string, string> = { rutin: "Kegiatan rutin", agenda: "Agenda", task: "Sesi lain" };

function menitKeJam(menit: number): string {
  const jam = Math.floor(menit / 60);
  return `${String(jam).padStart(2, "0")}:${String(menit % 60).padStart(2, "0")}`;
}

function DaftarBentrok({ bentrok }: { bentrok: Bentrok[] }) {
  return (
    <ul className="mt-2 space-y-1">
      {bentrok.map((b, i) => (
        <li key={i}>
          <span className="font-medium">{LABEL_JENIS[b.jenis] ?? b.jenis}:</span> {b.nama}{" "}
          <span className="whitespace-nowrap">({formatRentangJam(b.waktu_mulai, b.waktu_selesai)})</span>
        </li>
      ))}
    </ul>
  );
}

export default function PindahSesiModal({ sesi, onTutup }: { sesi: SesiRead; onTutup: () => void }) {
  const ubah = useUbahSesi();
  const durasi = Math.round(
    (parseWib(sesi.waktu_selesai).getTime() - parseWib(sesi.waktu_mulai).getTime()) / 60_000
  );

  const [tanggal, setTanggal] = useState(tanggalDari(sesi.waktu_mulai));
  const [mulai, setMulai] = useState(jamDari(sesi.waktu_mulai));
  const [selesai, setSelesai] = useState(jamDari(sesi.waktu_selesai));
  const [errorForm, setErrorForm] = useState("");

  function gantiMulai(nilai: string) {
    setMulai(nilai);
    // pertahankan durasi sesi bila masih di hari yang sama
    if (nilai) {
      const akhir = jamKeMenit(nilai) + durasi;
      if (akhir < 24 * 60) setSelesai(menitKeJam(akhir));
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setErrorForm("");
    if (!tanggal || !mulai || !selesai) {
      setErrorForm("Tanggal, jam mulai, dan jam selesai wajib diisi");
      return;
    }
    if (jamKeMenit(selesai) <= jamKeMenit(mulai)) {
      setErrorForm("Jam selesai harus setelah jam mulai");
      return;
    }
    const waktuMulai = gabungTanggalJam(tanggal, mulai);
    if (parseWib(waktuMulai).getTime() < Date.now()) {
      setErrorForm("Tidak bisa memindah ke waktu yang sudah lewat");
      return;
    }
    ubah.mutate(
      { idJadwal: sesi.id_jadwal, perubahan: { waktu_mulai: waktuMulai, waktu_selesai: gabungTanggalJam(tanggal, selesai) } },
      { onSuccess: onTutup }
    );
  }

  return (
    <Modal judul="Pindahkan sesi" onTutup={onTutup} kunci={ubah.isPending}>
      <p className="text-sm font-medium">{sesi.nama_task}</p>
      <p className="mt-1 text-xs text-[#8B857B]">
        Sekarang: {formatTanggal(sesi.waktu_mulai, { weekday: "long", day: "numeric", month: "long" })},{" "}
        {formatRentangJam(sesi.waktu_mulai, sesi.waktu_selesai)}
      </p>

      <form onSubmit={handleSubmit} noValidate className="mt-5 space-y-4">
        <div>
          <label htmlFor="pindah-tanggal" className={labelClass}>
            Tanggal
          </label>
          <input
            id="pindah-tanggal"
            type="date"
            value={tanggal}
            onChange={(event) => setTanggal(event.target.value)}
            className={inputClass}
          />
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label htmlFor="pindah-mulai" className={labelClass}>
              Mulai
            </label>
            <input
              id="pindah-mulai"
              type="time"
              value={mulai}
              onChange={(event) => gantiMulai(event.target.value)}
              className={inputClass}
            />
          </div>
          <div>
            <label htmlFor="pindah-selesai" className={labelClass}>
              Selesai
            </label>
            <input
              id="pindah-selesai"
              type="time"
              value={selesai}
              onChange={(event) => setSelesai(event.target.value)}
              className={inputClass}
            />
          </div>
        </div>
        {errorForm && <p className={fieldErrorClass}>{errorForm}</p>}

        {ubah.isError && (
          <div role="alert" className={errorBoxClass}>
            <p>{ubah.error.bentrok.length > 0 ? "Waktu itu bentrok dengan:" : ubah.error.message}</p>
            {ubah.error.bentrok.length > 0 && <DaftarBentrok bentrok={ubah.error.bentrok} />}
          </div>
        )}

        <div className="flex justify-end gap-3 pt-2">
          <button type="button" onClick={onTutup} disabled={ubah.isPending} className={secondaryButtonClass}>
            Batal
          </button>
          <button type="submit" disabled={ubah.isPending} className={primaryButtonClass}>
            {ubah.isPending ? "Memindahkan..." : "Pindahkan"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
