"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Sparkles } from "lucide-react";

import DashboardLayout from "../../../components/DashboardLayout";
import EstimasiWaktuLuang, { useEstimasiWaktuLuang } from "../../../components/planning/EstimasiWaktuLuang";
import WizardHeader from "../../../components/planning/WizardHeader";
import { useGoalWizard } from "../../../components/planning/useGoalWizard";
import {
  cardClass,
  errorBoxClass,
  fieldErrorClass,
  infoBoxClass,
  inputClass,
  labelClass,
  primaryButtonClass,
  secondaryButtonClass,
  warningBoxClass,
} from "../../../components/ui";
import { toApiError, type ApiError } from "../../../lib/api/client";
import { decomposeGoal } from "../../../lib/api/goals";
import { invalidateGoals, invalidateJadwal, queryKeys } from "../../../lib/api/queries";
import type { GoalDetail } from "../../../lib/api/types";
import { MENIT_HARIAN_MAKS, MENIT_HARIAN_MIN, jumlahTask } from "../../../lib/rencana";
import { formatTanggal } from "../../../lib/waktu";

/** Detik sejak `aktif` menjadi true (untuk indikator proses AI yang lama). */
function useDetikBerjalan(aktif: boolean): number {
  const [detik, setDetik] = useState(0);
  useEffect(() => {
    if (!aktif) return;
    const mulai = Date.now();
    const timer = setInterval(() => setDetik(Math.floor((Date.now() - mulai) / 1000)), 1000);
    return () => {
      clearInterval(timer);
      setDetik(0);
    };
  }, [aktif]);
  return detik;
}

/** Peringatan browser bila tab ditutup saat proses AI berjalan. */
function useCegahTutupTab(aktif: boolean) {
  useEffect(() => {
    if (!aktif) return;
    const handler = (event: BeforeUnloadEvent) => event.preventDefault();
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, [aktif]);
}

function petunjuk(error: ApiError): string | null {
  if (error.status === 422) return "Periksa deadline goal (langkah 1) atau waktu harianmu.";
  if (error.status === 502) return "Layanan AI sedang bermasalah. Tunggu sebentar lalu coba lagi.";
  if (error.status === 0) return "Jika proses sempat berjalan di server, rencananya akan muncul setelah halaman dimuat ulang.";
  return null;
}

export default function PlanningStep3() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { idGoal, goal } = useGoalWizard();
  const estimasi = useEstimasiWaktuLuang();

  const [manual, setManual] = useState(false);
  const [menitManual, setMenitManual] = useState("");
  const [errorMenit, setErrorMenit] = useState("");

  const decompose = useMutation<GoalDetail, ApiError, { replace: boolean }>({
    mutationFn: async ({ replace }) => {
      try {
        return await decomposeGoal(idGoal as number, {
          menitHarian: manual ? Number(menitManual) : null,
          replace,
        });
      } catch (err) {
        throw toApiError(err);
      }
    },
    onSuccess: async (detail) => {
      queryClient.setQueryData(queryKeys.goal(detail.id_goal), detail);
      // replace menghapus milestone lama beserta sesi jadwalnya
      await Promise.all([invalidateGoals(queryClient), invalidateJadwal(queryClient)]);
      router.push("/planning/step-4");
    },
    onError: () => {
      // 409 / timeout di browser: rencana mungkin sudah ada di server → tampilkan keadaan terbaru
      void goal.refetch();
    },
  });

  const berjalan = decompose.isPending;
  const detik = useDetikBerjalan(berjalan);
  useCegahTutupTab(berjalan);

  const sudahAda = (goal.data?.milestones.length ?? 0) > 0;

  function jalankan(replace: boolean) {
    setErrorMenit("");
    if (manual) {
      const nilai = Number(menitManual);
      if (!Number.isInteger(nilai) || nilai < MENIT_HARIAN_MIN || nilai > MENIT_HARIAN_MAKS) {
        setErrorMenit(`Isi angka bulat ${MENIT_HARIAN_MIN}–${MENIT_HARIAN_MAKS} menit`);
        return;
      }
    }
    if (
      replace &&
      !window.confirm(
        "Rencana lama beserta task dan jadwal sesinya akan dihapus dan diganti rencana baru. Lanjutkan?"
      )
    ) {
      return;
    }
    decompose.mutate({ replace });
  }

  return (
    <DashboardLayout>
      <div className="mx-auto max-w-5xl">
        <WizardHeader
          langkah={3}
          judul="Susun Rencana dengan AI"
          subjudul="AI memecah goal-mu menjadi target bulanan dan mingguan, lalu merinci task untuk minggu ini."
        />

        {goal.isPending ? (
          <p className="mt-7 text-sm text-[#8B857B]">Memuat goal...</p>
        ) : goal.isError ? (
          <p role="alert" className={`mt-7 ${errorBoxClass}`}>
            {goal.error.message}
          </p>
        ) : (
          <div className="mt-7 grid gap-5 lg:grid-cols-2">
            <section className={cardClass}>
              <p className="text-xs font-semibold uppercase tracking-wide text-[#8B857B]">Goal</p>
              <p className="mt-2 text-lg font-medium">{goal.data.judul_goal}</p>
              {goal.data.deskripsi && <p className="mt-2 text-sm text-[#64675E]">{goal.data.deskripsi}</p>}
              {goal.data.deadline && (
                <p className="mt-3 text-sm text-[#8B857B]">Deadline: {formatTanggal(goal.data.deadline)}</p>
              )}
              <Link href="/planning/step-1" className="mt-4 inline-block text-sm font-medium text-[#506851] underline">
                Ubah goal
              </Link>
            </section>

            <section className={`${cardClass} space-y-5`}>
              <EstimasiWaktuLuang />

              <label className="flex cursor-pointer items-center gap-3 text-sm">
                <input
                  type="checkbox"
                  checked={manual}
                  disabled={berjalan}
                  onChange={(event) => {
                    setManual(event.target.checked);
                    if (event.target.checked && !menitManual && estimasi.menit) {
                      setMenitManual(String(Math.max(estimasi.menit, MENIT_HARIAN_MIN)));
                    }
                  }}
                  className="h-4 w-4 accent-[#82947B]"
                />
                Atur sendiri waktu yang ingin kupakai untuk goal ini per hari
              </label>

              {manual && (
                <div className="sm:max-w-xs">
                  <label htmlFor="menit-harian" className={labelClass}>
                    Menit per hari
                  </label>
                  <input
                    id="menit-harian"
                    type="number"
                    inputMode="numeric"
                    min={MENIT_HARIAN_MIN}
                    max={MENIT_HARIAN_MAKS}
                    step={5}
                    disabled={berjalan}
                    value={menitManual}
                    onChange={(event) => setMenitManual(event.target.value)}
                    className={inputClass}
                  />
                  <p className="mt-1 text-xs text-[#8B857B]">
                    {MENIT_HARIAN_MIN}–{MENIT_HARIAN_MAKS} menit. Kosongkan centang untuk memakai perkiraan otomatis.
                  </p>
                  {errorMenit && <p className={fieldErrorClass}>{errorMenit}</p>}
                </div>
              )}
            </section>
          </div>
        )}

        {sudahAda && goal.data && !berjalan && (
          <div className={`mt-5 ${infoBoxClass}`}>
            <p>
              Goal ini sudah punya rencana AI ({goal.data.milestones.length} target, {jumlahTask(goal.data.milestones)}{" "}
              task). Kamu bisa meninjaunya, atau menyusun ulang dari awal.
            </p>
          </div>
        )}

        {berjalan && (
          <div role="status" className={`mt-5 flex items-start gap-3 ${infoBoxClass}`}>
            <Sparkles size={18} className="mt-0.5 shrink-0 animate-pulse" />
            <div>
              <p className="font-medium">AI sedang menyusun rencanamu... ({detik} detik)</p>
              <p className="mt-1">
                Biasanya kurang dari satu menit, tapi bisa beberapa menit bila layanan AI sedang sibuk. Jangan tutup
                halaman ini.
              </p>
            </div>
          </div>
        )}

        {decompose.isError && (
          <div role="alert" className={`mt-5 ${decompose.error.status === 409 ? warningBoxClass : errorBoxClass}`}>
            <p>{decompose.error.message}</p>
            {petunjuk(decompose.error) && <p className="mt-1">{petunjuk(decompose.error)}</p>}
          </div>
        )}

        <div className="mt-8 flex flex-wrap items-center justify-between gap-4">
          <Link href="/planning/step-2" className={secondaryButtonClass}>
            ← Kembali
          </Link>

          <div className="flex flex-wrap gap-3">
            {sudahAda ? (
              <>
                <button
                  type="button"
                  disabled={berjalan}
                  onClick={() => jalankan(true)}
                  className={secondaryButtonClass}
                >
                  Susun ulang dari awal
                </button>
                <button
                  type="button"
                  disabled={berjalan}
                  onClick={() => router.push("/planning/step-4")}
                  className={primaryButtonClass}
                >
                  Tinjau rencana →
                </button>
              </>
            ) : (
              <button
                type="button"
                disabled={berjalan || !goal.data}
                onClick={() => jalankan(false)}
                className={primaryButtonClass}
              >
                {berjalan ? "Menyusun..." : "Susun rencana dengan AI"}
              </button>
            )}
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}
