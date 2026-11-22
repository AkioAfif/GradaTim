"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";

import DashboardLayout from "../../../components/DashboardLayout";
import RencanaGoalTree from "../../../components/goal/RencanaGoalTree";
import WizardHeader from "../../../components/planning/WizardHeader";
import { useGoalWizard } from "../../../components/planning/useGoalWizard";
import {
  errorBoxClass,
  infoBoxClass,
  primaryButtonClass,
  secondaryButtonClass,
} from "../../../components/ui";
import { jumlahTask, mingguanPada } from "../../../lib/rencana";
import { hariIniWib } from "../../../lib/waktu";

export default function PlanningStep4() {
  const router = useRouter();
  const { goal } = useGoalWizard();

  const detail = goal.data;
  const adaRencana = (detail?.milestones.length ?? 0) > 0;
  const tugasMingguIni = detail ? mingguanPada(detail.milestones, hariIniWib())?.tasks.length ?? 0 : 0;

  return (
    <DashboardLayout>
      <div className="mx-auto max-w-5xl">
        <WizardHeader
          langkah={4}
          judul="Tinjau Rencanamu"
          subjudul="Target besar sudah dipecah menjadi langkah kecil. Task minggu berikutnya dirinci setiap minggu, menyesuaikan progresmu."
        />

        <div className="mt-7">
          {goal.isPending ? (
            <p className="text-sm text-[#8B857B]">Memuat rencana...</p>
          ) : goal.isError ? (
            <p role="alert" className={errorBoxClass}>
              {goal.error.message}
            </p>
          ) : !adaRencana ? (
            <div className={infoBoxClass}>
              Goal ini belum punya rencana.{" "}
              <Link href="/planning/step-3" className="font-medium underline">
                Susun dengan AI
              </Link>
            </div>
          ) : (
            <>
              <div className="mb-5 flex flex-wrap gap-x-6 gap-y-1 text-sm text-[#64675E]">
                <span>
                  <strong>{detail?.judul_goal}</strong>
                </span>
                <span>{jumlahTask(detail?.milestones ?? [])} task dirinci</span>
                <span>{tugasMingguIni} task minggu ini</span>
              </div>
              {detail && <RencanaGoalTree goal={detail} />}
            </>
          )}
        </div>

        <div className="mt-8 flex flex-wrap items-center justify-between gap-4">
          <Link href="/planning/step-3" className={secondaryButtonClass}>
            ← Kembali
          </Link>
          <button
            type="button"
            disabled={!adaRencana}
            onClick={() => router.push("/planning/step-5")}
            className={primaryButtonClass}
          >
            Lanjut ke penjadwalan →
          </button>
        </div>
      </div>
    </DashboardLayout>
  );
}
