"use client";

import { useEffect, useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";

import DashboardLayout from "../../../components/DashboardLayout";
import WizardHeader from "../../../components/planning/WizardHeader";
import {
  cardClass,
  errorBoxClass,
  fieldErrorClass,
  infoBoxClass,
  inputClass,
  labelClass,
  primaryButtonClass,
  secondaryButtonClass,
} from "../../../components/ui";
import { ApiError, toApiError } from "../../../lib/api/client";
import { createGoal, updateGoal } from "../../../lib/api/goals";
import { invalidateGoals, queryKeys, useGoal } from "../../../lib/api/queries";
import type { GoalRead } from "../../../lib/api/types";
import { clearIdGoalWizard, setIdGoalWizard, useIdGoalWizard } from "../../../lib/planning";
import { hariIniWib, tanggalDari } from "../../../lib/waktu";

// Batas sama dengan schemas/goal.py
const JUDUL_MIN = 3;
const JUDUL_MAKS = 255;
const DESKRIPSI_MAKS = 2000;

function GoalForm({ awal }: { awal: GoalRead | null }) {
  const router = useRouter();
  const queryClient = useQueryClient();

  const deadlineAwal = awal?.deadline ? tanggalDari(awal.deadline) : "";
  const [judul, setJudul] = useState(awal?.judul_goal ?? "");
  const [deskripsi, setDeskripsi] = useState(awal?.deskripsi ?? "");
  const [deadline, setDeadline] = useState(deadlineAwal);
  const [error, setError] = useState("");
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [menyimpan, setMenyimpan] = useState(false);

  const hariIni = hariIniWib();

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");

    const judulBersih = judul.trim();
    const errors: Record<string, string> = {};
    if (judulBersih.length < JUDUL_MIN) errors.judul_goal = `Judul minimal ${JUDUL_MIN} karakter`;
    if (!deadline) errors.deadline = "Deadline wajib diisi";
    else if (deadline !== deadlineAwal && deadline < hariIni) errors.deadline = "Deadline tidak boleh di masa lalu";
    setFieldErrors(errors);
    if (Object.keys(errors).length > 0) return;

    setMenyimpan(true);
    try {
      const deskripsiBersih = deskripsi.trim() || null;
      let goal: GoalRead;
      if (awal) {
        // deadline hanya dikirim bila berubah: deadline lama yang sudah lewat akan ditolak backend
        goal = await updateGoal(awal.id_goal, {
          judul_goal: judulBersih,
          deskripsi: deskripsiBersih,
          ...(deadline !== deadlineAwal ? { deadline } : {}),
        });
      } else {
        goal = await createGoal({ judul_goal: judulBersih, deskripsi: deskripsiBersih, deadline });
        setIdGoalWizard(goal.id_goal);
      }
      await invalidateGoals(queryClient);
      await queryClient.invalidateQueries({ queryKey: queryKeys.goal(goal.id_goal) });
      router.push("/planning/step-2");
    } catch (err) {
      const apiError = toApiError(err);
      if (apiError instanceof ApiError && Object.keys(apiError.fieldErrors).length > 0) {
        setFieldErrors(apiError.fieldErrors);
      } else {
        setError(apiError.message);
      }
    } finally {
      setMenyimpan(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} noValidate>
      <div className={`mt-7 ${cardClass}`}>
        <div>
          <label htmlFor="judul" className={labelClass}>
            Judul Goal
          </label>
          <input
            id="judul"
            required
            maxLength={JUDUL_MAKS}
            value={judul}
            onChange={(event) => setJudul(event.target.value)}
            placeholder="Contoh: Menguasai dasar machine learning"
            className={inputClass}
          />
          {fieldErrors.judul_goal && <p className={fieldErrorClass}>{fieldErrors.judul_goal}</p>}
        </div>

        <div className="mt-6">
          <label htmlFor="deskripsi" className={labelClass}>
            Deskripsi <span className="font-normal text-[#8B857B]">(opsional)</span>
          </label>
          <textarea
            id="deskripsi"
            rows={4}
            maxLength={DESKRIPSI_MAKS}
            value={deskripsi}
            onChange={(event) => setDeskripsi(event.target.value)}
            placeholder="Apa yang ingin kamu capai, kondisimu sekarang, atau hal yang perlu diperhatikan AI."
            className={inputClass}
          />
          <p className="mt-1 text-xs text-[#8B857B]">
            Semakin jelas deskripsinya, semakin tepat rencana dari AI.
          </p>
          {fieldErrors.deskripsi && <p className={fieldErrorClass}>{fieldErrors.deskripsi}</p>}
        </div>

        <div className="mt-6 sm:max-w-xs">
          <label htmlFor="deadline" className={labelClass}>
            Target Deadline
          </label>
          <input
            id="deadline"
            type="date"
            required
            min={hariIni}
            value={deadline}
            onChange={(event) => setDeadline(event.target.value)}
            className={inputClass}
          />
          {fieldErrors.deadline && <p className={fieldErrorClass}>{fieldErrors.deadline}</p>}
        </div>
      </div>

      {error && (
        <p role="alert" className={`mt-5 ${errorBoxClass}`}>
          {error}
        </p>
      )}

      <div className="mt-5 flex items-center justify-between gap-4">
        <Link href="/" className={secondaryButtonClass}>
          ← Kembali
        </Link>

        <button type="submit" disabled={menyimpan} className={primaryButtonClass}>
          {menyimpan ? "Menyimpan..." : "Simpan & Lanjut →"}
        </button>
      </div>
    </form>
  );
}

export default function PlanningStep1() {
  const idGoal = useIdGoalWizard();
  const goal = useGoal(idGoal ?? null);
  const hilang = goal.error instanceof ApiError && goal.error.status === 404;

  // Goal di wizard sudah dihapus: mulai dari goal baru.
  useEffect(() => {
    if (hilang) clearIdGoalWizard();
  }, [hilang]);

  const memuat = idGoal === undefined || (idGoal !== null && goal.isPending && !hilang);
  const awal = idGoal !== null && !hilang ? goal.data ?? null : null;

  return (
    <DashboardLayout>
      <div className="mx-auto max-w-5xl">
        <WizardHeader
          langkah={1}
          judul="Apa Goal-mu?"
          subjudul="Tulis target besarmu. AI akan memecahnya menjadi target bulanan, mingguan, dan task kecil."
        />

        {awal && (
          <div className={`mt-6 flex flex-wrap items-center justify-between gap-3 ${infoBoxClass}`}>
            <span>
              Melanjutkan rencana <strong>{awal.judul_goal}</strong>.
            </span>
            <button
              type="button"
              onClick={clearIdGoalWizard}
              className="font-medium underline underline-offset-2"
            >
              Buat goal baru
            </button>
          </div>
        )}

        {goal.isError && !hilang && (
          <p role="alert" className={`mt-6 ${errorBoxClass}`}>
            {goal.error.message}
          </p>
        )}

        {memuat ? (
          <p className="mt-7 text-sm text-[#8B857B]">Memuat...</p>
        ) : (
          <GoalForm key={awal?.id_goal ?? "baru"} awal={awal} />
        )}
      </div>
    </DashboardLayout>
  );
}
