"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import DashboardLayout from "../../../components/DashboardLayout";
import HasilPenjadwalan from "../../../components/jadwal/HasilPenjadwalan";
import WizardHeader from "../../../components/planning/WizardHeader";
import { useGoalWizard } from "../../../components/planning/useGoalWizard";
import {
  cardClass,
  errorBoxClass,
  primaryButtonClass,
  secondaryButtonClass,
} from "../../../components/ui";
import { toApiError, type ApiError } from "../../../lib/api/client";
import { jadwalkanGoal } from "../../../lib/api/jadwal";
import { invalidateJadwal } from "../../../lib/api/queries";
import type { HasilPenjadwalanRead } from "../../../lib/api/types";
import { clearIdGoalWizard } from "../../../lib/planning";

export default function PlanningStep5() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [selesaiDitekan, setSelesaiDitekan] = useState(false);
  const { idGoal, goal } = useGoalWizard({ selesai: selesaiDitekan });

  const jadwalkan = useMutation<HasilPenjadwalanRead, ApiError>({
    mutationFn: async () => {
      try {
        return await jadwalkanGoal(idGoal as number);
      } catch (err) {
        throw toApiError(err);
      }
    },
    onSuccess: () => invalidateJadwal(queryClient),
  });

  function selesai() {
    // dalam satu event handler: render berikutnya sudah membawa selesai=true, jadi hook tidak
    // sempat mengalihkan ke langkah 1 saat id_goal dihapus
    setSelesaiDitekan(true);
    clearIdGoalWizard();
    router.push("/calendar");
  }

  return (
    <DashboardLayout>
      <div className="mx-auto max-w-5xl">
        <WizardHeader
          langkah={5}
          judul="Jadwalkan Minggu Ini"
          subjudul="Task minggu ini ditempatkan otomatis di slot kosong kalendermu, di luar kegiatan rutin dan agenda."
        />

        <section className={`mt-7 ${cardClass}`}>
          {goal.data && (
            <p className="text-sm text-[#64675E]">
              Goal: <strong>{goal.data.judul_goal}</strong>
            </p>
          )}

          <ul className="mt-4 list-disc space-y-1.5 pl-5 text-sm text-[#64675E]">
            <li>Hanya task minggu ini yang dijadwalkan. Task minggu berikutnya dirinci dan dijadwalkan saat minggunya tiba.</li>
            <li>Setelah sesi berlangsung, tandai <strong>Selesai</strong> atau <strong>Tidak dikerjakan</strong> di kalender (maksimal 48 jam setelah sesi berakhir).</li>
            <li>Sebagian sesi dapat ditempatkan di waktu acak untuk keperluan riset personalisasi jadwal.</li>
          </ul>

          <div className="mt-6">
            {jadwalkan.isSuccess ? (
              <HasilPenjadwalan sesiBaru={jadwalkan.data.sesi_baru} tidakMuat={jadwalkan.data.tidak_muat} />
            ) : (
              <button
                type="button"
                disabled={jadwalkan.isPending || idGoal === null}
                onClick={() => jadwalkan.mutate()}
                className={primaryButtonClass}
              >
                {jadwalkan.isPending ? "Menjadwalkan..." : "Jadwalkan sekarang"}
              </button>
            )}
          </div>

          {jadwalkan.isError && (
            <p role="alert" className={`mt-4 ${errorBoxClass}`}>
              {jadwalkan.error.message}
            </p>
          )}
        </section>

        <div className="mt-8 flex flex-wrap items-center justify-between gap-4">
          <Link href="/planning/step-4" className={secondaryButtonClass}>
            ← Kembali
          </Link>
          <button
            type="button"
            disabled={!jadwalkan.isSuccess}
            onClick={selesai}
            className={primaryButtonClass}
          >
            Selesai, lihat kalender →
          </button>
        </div>
      </div>
    </DashboardLayout>
  );
}
