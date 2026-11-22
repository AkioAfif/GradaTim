"use client";

import { useState, type FormEvent } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import Modal from "../Modal";
import {
  errorBoxClass,
  fieldErrorClass,
  inputClass,
  labelClass,
  primaryButtonClass,
  secondaryButtonClass,
  warningBoxClass,
} from "../ui";
import { createAgenda } from "../../lib/api/agenda";
import { toApiError, type ApiError } from "../../lib/api/client";
import { getJadwalMinggu } from "../../lib/api/jadwal";
import { invalidateJadwal, useJadwalMinggu } from "../../lib/api/queries";
import type { AgendaCreate, AgendaRead, SesiRead } from "../../lib/api/types";
import { awalMinggu, gabungTanggalJam, jamKeMenit, parseWib, tanggalDari } from "../../lib/waktu";
import { useSekarang } from "./hooks";
import SesiCard from "./SesiCard";

type HasilSimpan = {
  agenda: AgendaRead;
  /** Sesi task terjadwal yang tertimpa agenda — backend hanya memeriksa rutin & agenda lain. */
  sesiTertimpa: SesiRead[];
};

/** Sesi `terjadwal` minggu agenda itu yang beririsan dengan rentang agenda. */
async function cariSesiTertimpa(agenda: AgendaRead): Promise<SesiRead[]> {
  try {
    const jadwal = await getJadwalMinggu(tanggalDari(agenda.waktu_mulai));
    const mulai = parseWib(agenda.waktu_mulai).getTime();
    const selesai = parseWib(agenda.waktu_selesai).getTime();
    return jadwal.sesi.filter(
      (s) =>
        s.status === "terjadwal" &&
        parseWib(s.waktu_mulai).getTime() < selesai &&
        parseWib(s.waktu_selesai).getTime() > mulai
    );
  } catch {
    return []; // pemeriksaan tambahan; agenda sudah tersimpan
  }
}

/**
 * Tambah agenda (acara sekali jalan). Agenda tetap disimpan walau bentrok; peringatan dari backend
 * (rutin & agenda lain) dan sesi task yang tertimpa ditampilkan, sesi bisa langsung dipindah.
 */
export default function AgendaModal({ tanggalAwal, onTutup }: { tanggalAwal: string; onTutup: () => void }) {
  const queryClient = useQueryClient();
  const sekarang = useSekarang();
  const [nama, setNama] = useState("");
  const [tanggal, setTanggal] = useState(tanggalAwal);
  const [mulai, setMulai] = useState("");
  const [selesai, setSelesai] = useState("");
  const [errorForm, setErrorForm] = useState("");

  const simpan = useMutation<HasilSimpan, ApiError, AgendaCreate>({
    mutationFn: async (payload) => {
      let agenda: AgendaRead;
      try {
        agenda = await createAgenda(payload);
      } catch (err) {
        throw toApiError(err);
      }
      return { agenda, sesiTertimpa: await cariSesiTertimpa(agenda) };
    },
    onSuccess: async ({ agenda, sesiTertimpa }) => {
      await invalidateJadwal(queryClient);
      if (agenda.peringatan_bentrok.length === 0 && sesiTertimpa.length === 0) onTutup();
    },
  });

  // Kartu sesi tertimpa memakai data kalender terbaru (status/waktu berubah setelah dipindah).
  const tanggalAgenda = simpan.data ? tanggalDari(simpan.data.agenda.waktu_mulai) : tanggalAwal;
  const jadwalTerkini = useJadwalMinggu(awalMinggu(tanggalAgenda), simpan.isSuccess);
  const sesiTertimpa = (simpan.data?.sesiTertimpa ?? []).map(
    (s) => jadwalTerkini.data?.sesi.find((t) => t.id_jadwal === s.id_jadwal) ?? s
  );

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setErrorForm("");
    if (!nama.trim() || !tanggal || !mulai || !selesai) {
      setErrorForm("Semua kolom wajib diisi");
      return;
    }
    if (jamKeMenit(selesai) <= jamKeMenit(mulai)) {
      setErrorForm("Jam selesai harus setelah jam mulai (agenda harus selesai di hari yang sama)");
      return;
    }
    simpan.mutate({
      nama: nama.trim(),
      waktu_mulai: gabungTanggalJam(tanggal, mulai),
      waktu_selesai: gabungTanggalJam(tanggal, selesai),
    });
  }

  const peringatan = simpan.data?.agenda.peringatan_bentrok ?? [];

  return (
    <Modal judul="Tambah agenda" onTutup={onTutup} kunci={simpan.isPending}>
      {simpan.isSuccess && (peringatan.length > 0 || sesiTertimpa.length > 0) ? (
        <div className="space-y-4">
          {peringatan.length > 0 && (
            <div className={warningBoxClass}>
              <p className="font-medium">Agenda disimpan, tapi bentrok dengan:</p>
              <ul className="mt-1 list-disc pl-5">
                {peringatan.map((p, i) => (
                  <li key={i}>{p}</li>
                ))}
              </ul>
            </div>
          )}
          {sesiTertimpa.length > 0 && (
            <div>
              <p className={warningBoxClass}>
                Agenda disimpan dan menimpa {sesiTertimpa.length} sesi task. Pindahkan sesinya agar tetap bisa
                dikerjakan:
              </p>
              <div className="mt-3 space-y-3">
                {sesiTertimpa.map((s) => (
                  <SesiCard key={s.id_jadwal} sesi={s} sekarang={sekarang} tampilTanggal />
                ))}
              </div>
            </div>
          )}
          <div className="flex justify-end">
            <button type="button" onClick={onTutup} className={primaryButtonClass}>
              Mengerti
            </button>
          </div>
        </div>
      ) : (
        <form onSubmit={handleSubmit} noValidate className="space-y-4">
          <p className="text-sm text-[#8B857B]">
            Acara sekali jalan (rapat, ujian, janji). Task tidak akan dijadwalkan di jam ini.
          </p>
          <div>
            <label htmlFor="agenda-nama" className={labelClass}>
              Nama agenda
            </label>
            <input
              id="agenda-nama"
              maxLength={100}
              value={nama}
              onChange={(event) => setNama(event.target.value)}
              placeholder="Contoh: Rapat organisasi"
              className={inputClass}
            />
          </div>
          <div>
            <label htmlFor="agenda-tanggal" className={labelClass}>
              Tanggal
            </label>
            <input
              id="agenda-tanggal"
              type="date"
              value={tanggal}
              onChange={(event) => setTanggal(event.target.value)}
              className={inputClass}
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label htmlFor="agenda-mulai" className={labelClass}>
                Mulai
              </label>
              <input
                id="agenda-mulai"
                type="time"
                value={mulai}
                onChange={(event) => setMulai(event.target.value)}
                className={inputClass}
              />
            </div>
            <div>
              <label htmlFor="agenda-selesai" className={labelClass}>
                Selesai
              </label>
              <input
                id="agenda-selesai"
                type="time"
                value={selesai}
                onChange={(event) => setSelesai(event.target.value)}
                className={inputClass}
              />
            </div>
          </div>
          {errorForm && <p className={fieldErrorClass}>{errorForm}</p>}
          {simpan.isError && (
            <p role="alert" className={errorBoxClass}>
              {simpan.error.message}
            </p>
          )}
          <div className="flex justify-end gap-3 pt-2">
            <button type="button" onClick={onTutup} disabled={simpan.isPending} className={secondaryButtonClass}>
              Batal
            </button>
            <button type="submit" disabled={simpan.isPending} className={primaryButtonClass}>
              {simpan.isPending ? "Menyimpan..." : "Simpan agenda"}
            </button>
          </div>
        </form>
      )}
    </Modal>
  );
}
