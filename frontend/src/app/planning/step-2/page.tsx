"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { Trash2 } from "lucide-react";

import DashboardLayout from "../../../components/DashboardLayout";
import EstimasiWaktuLuang from "../../../components/planning/EstimasiWaktuLuang";
import WizardHeader from "../../../components/planning/WizardHeader";
import { useGoalWizard } from "../../../components/planning/useGoalWizard";
import {
  cardClass,
  errorBoxClass,
  fieldErrorClass,
  inputClass,
  labelClass,
  primaryButtonClass,
  secondaryButtonClass,
} from "../../../components/ui";
import { toApiError } from "../../../lib/api/client";
import { invalidateJadwal, queryKeys, useTimeConstraints } from "../../../lib/api/queries";
import { createTimeConstraint, deleteTimeConstraint } from "../../../lib/api/timeConstraints";
import type { TimeConstraintRead } from "../../../lib/api/types";
import { NAMA_HARI, NAMA_HARI_PENDEK, formatJam, jamKeMenit } from "../../../lib/waktu";

function KegiatanForm({ onTersimpan }: { onTersimpan: () => Promise<void> }) {
  const [nama, setNama] = useState("");
  const [hari, setHari] = useState<number[]>([]);
  const [mulai, setMulai] = useState("");
  const [selesai, setSelesai] = useState("");
  const [error, setError] = useState("");
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [menyimpan, setMenyimpan] = useState(false);

  const lewatTengahMalam = mulai && selesai && jamKeMenit(selesai) < jamKeMenit(mulai);

  function toggleHari(indeks: number) {
    setHari((sebelum) =>
      sebelum.includes(indeks) ? sebelum.filter((h) => h !== indeks) : [...sebelum, indeks].sort()
    );
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");

    const errors: Record<string, string> = {};
    if (!nama.trim()) errors.nama = "Nama kegiatan wajib diisi";
    if (hari.length === 0) errors.hari = "Pilih minimal satu hari";
    if (!mulai || !selesai) errors.jam = "Jam mulai dan selesai wajib diisi";
    else if (mulai === selesai) errors.jam = "Jam mulai dan selesai tidak boleh sama";
    setFieldErrors(errors);
    if (Object.keys(errors).length > 0) return;

    setMenyimpan(true);
    const gagal: string[] = [];
    // satu baris time_constraint per hari
    for (const h of hari) {
      try {
        await createTimeConstraint({
          nama: nama.trim(),
          hari_dalam_minggu: h,
          waktu_mulai: mulai,
          waktu_selesai: selesai,
        });
      } catch (err) {
        gagal.push(`${NAMA_HARI[h]}: ${toApiError(err).message}`);
      }
    }
    await onTersimpan();
    setMenyimpan(false);

    if (gagal.length > 0) {
      setError(`Sebagian gagal disimpan — ${gagal.join("; ")}`);
      return;
    }
    setNama("");
    setHari([]);
    setMulai("");
    setSelesai("");
  }

  return (
    <form onSubmit={handleSubmit} noValidate className="space-y-5">
      <div>
        <label htmlFor="nama-kegiatan" className={labelClass}>
          Nama kegiatan
        </label>
        <input
          id="nama-kegiatan"
          maxLength={100}
          value={nama}
          onChange={(event) => setNama(event.target.value)}
          placeholder="Contoh: Kuliah, Kerja, Gym"
          className={inputClass}
        />
        {fieldErrors.nama && <p className={fieldErrorClass}>{fieldErrors.nama}</p>}
      </div>

      <fieldset>
        <legend className={labelClass}>Hari</legend>
        <div className="flex flex-wrap gap-2">
          {NAMA_HARI_PENDEK.map((label, indeks) => (
            <label
              key={label}
              className={`cursor-pointer rounded-full px-4 py-2 text-sm ${
                hari.includes(indeks) ? "bg-[#F0C4A4] text-[#45382E]" : "bg-[#ECE9E1] text-[#57564F]"
              }`}
            >
              <input
                type="checkbox"
                checked={hari.includes(indeks)}
                onChange={() => toggleHari(indeks)}
                className="sr-only"
              />
              {label}
            </label>
          ))}
        </div>
        {fieldErrors.hari && <p className={fieldErrorClass}>{fieldErrors.hari}</p>}
      </fieldset>

      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <label htmlFor="jam-mulai" className={labelClass}>
            Jam mulai
          </label>
          <input
            id="jam-mulai"
            type="time"
            value={mulai}
            onChange={(event) => setMulai(event.target.value)}
            className={inputClass}
          />
        </div>
        <div>
          <label htmlFor="jam-selesai" className={labelClass}>
            Jam selesai
          </label>
          <input
            id="jam-selesai"
            type="time"
            value={selesai}
            onChange={(event) => setSelesai(event.target.value)}
            className={inputClass}
          />
        </div>
      </div>
      {fieldErrors.jam && <p className={fieldErrorClass}>{fieldErrors.jam}</p>}
      {lewatTengahMalam && (
        <p className="text-xs text-[#8B857B]">Kegiatan ini melewati tengah malam (selesai keesokan harinya).</p>
      )}

      {error && (
        <p role="alert" className={errorBoxClass}>
          {error}
        </p>
      )}

      <button type="submit" disabled={menyimpan} className={primaryButtonClass}>
        {menyimpan ? "Menyimpan..." : "+ Tambah kegiatan"}
      </button>
    </form>
  );
}

function DaftarKegiatan({
  kegiatan,
  onHapus,
  menghapus,
}: {
  kegiatan: TimeConstraintRead[];
  onHapus: (item: TimeConstraintRead) => void;
  menghapus: number | null;
}) {
  if (kegiatan.length === 0) {
    return (
      <p className="text-sm text-[#8B857B]">
        Belum ada kegiatan rutin. Kalau jadwalmu kosong, langkah ini boleh dilewati.
      </p>
    );
  }

  return (
    <div className="space-y-4">
      {NAMA_HARI.map((namaHari, indeks) => {
        const hariIni = kegiatan.filter((k) => k.hari_dalam_minggu === indeks);
        if (hariIni.length === 0) return null;
        return (
          <div key={namaHari}>
            <p className="text-xs font-semibold uppercase tracking-wide text-[#8B857B]">{namaHari}</p>
            <ul className="mt-2 divide-y divide-[#EBE2D6] rounded-lg border border-[#EBE2D6] bg-white">
              {hariIni.map((k) => (
                <li key={k.id_constraint} className="flex items-center justify-between gap-3 px-4 py-3 text-sm">
                  <span>
                    <span className="font-medium">{k.nama}</span>{" "}
                    <span className="text-[#8B857B]">
                      {formatJam(k.waktu_mulai)}–{formatJam(k.waktu_selesai)}
                    </span>
                  </span>
                  <button
                    type="button"
                    onClick={() => onHapus(k)}
                    disabled={menghapus === k.id_constraint}
                    aria-label={`Hapus ${k.nama} hari ${namaHari}`}
                    title="Hapus"
                    className="rounded-md p-1.5 text-[#A24A3A] hover:bg-[#F8E1DA] disabled:opacity-50"
                  >
                    <Trash2 size={16} />
                  </button>
                </li>
              ))}
            </ul>
          </div>
        );
      })}
    </div>
  );
}

export default function PlanningStep2() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { idGoal } = useGoalWizard();
  const rutin = useTimeConstraints();
  const [menghapus, setMenghapus] = useState<number | null>(null);
  const [errorHapus, setErrorHapus] = useState("");

  async function segarkan() {
    await queryClient.invalidateQueries({ queryKey: queryKeys.timeConstraints });
    await invalidateJadwal(queryClient); // kegiatan rutin ikut tampil di kalender
  }

  async function hapus(item: TimeConstraintRead) {
    setErrorHapus("");
    setMenghapus(item.id_constraint);
    try {
      await deleteTimeConstraint(item.id_constraint);
      await segarkan();
    } catch (err) {
      setErrorHapus(toApiError(err).message);
    } finally {
      setMenghapus(null);
    }
  }

  return (
    <DashboardLayout>
      <div className="mx-auto max-w-5xl">
        <WizardHeader
          langkah={2}
          judul="Kegiatan Rutin"
          subjudul="Isi kegiatan yang berulang tiap minggu (kuliah, kerja, olahraga). Task tidak akan dijadwalkan di jam ini. Berlaku untuk semua goal-mu."
        />

        <div className="mt-7 grid gap-5 lg:grid-cols-[1fr_1.1fr]">
          <section className={cardClass}>
            <h2 className="mb-5 text-base font-semibold">Tambah kegiatan</h2>
            <KegiatanForm onTersimpan={segarkan} />
          </section>

          <section className={`${cardClass} space-y-6`}>
            <EstimasiWaktuLuang />
            <div>
              <h2 className="mb-3 text-base font-semibold">Kegiatan rutinmu</h2>
              {rutin.isPending ? (
                <p className="text-sm text-[#8B857B]">Memuat...</p>
              ) : rutin.isError ? (
                <p role="alert" className={errorBoxClass}>
                  {rutin.error.message}
                </p>
              ) : (
                <DaftarKegiatan kegiatan={rutin.data} onHapus={hapus} menghapus={menghapus} />
              )}
              {errorHapus && (
                <p role="alert" className={`mt-3 ${errorBoxClass}`}>
                  {errorHapus}
                </p>
              )}
            </div>
          </section>
        </div>

        <div className="mt-8 flex items-center justify-between gap-4">
          <Link href="/planning/step-1" className={secondaryButtonClass}>
            ← Kembali
          </Link>
          <button
            type="button"
            disabled={idGoal === null}
            onClick={() => router.push("/planning/step-3")}
            className={primaryButtonClass}
          >
            Lanjut →
          </button>
        </div>
      </div>
    </DashboardLayout>
  );
}
