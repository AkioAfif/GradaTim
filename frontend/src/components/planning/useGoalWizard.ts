"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

import { useGoal } from "../../lib/api/queries";
import { ApiError } from "../../lib/api/client";
import { clearIdGoalWizard, useIdGoalWizard } from "../../lib/planning";

/**
 * Untuk langkah 2–5: goal yang sedang direncanakan. Tanpa goal di wizard (atau goal sudah
 * dihapus → 404), user dikembalikan ke langkah 1.
 *
 * `selesai`: wizard sengaja ditutup (id_goal dihapus lalu pindah halaman) — jangan redirect ke
 * langkah 1, supaya tidak mendahului navigasi tujuan.
 */
export function useGoalWizard({ selesai = false }: { selesai?: boolean } = {}) {
  const router = useRouter();
  const idGoal = useIdGoalWizard();
  const goal = useGoal(idGoal ?? null);
  const hilang = goal.error instanceof ApiError && goal.error.status === 404;

  useEffect(() => {
    if (selesai) return;
    if (idGoal === null) {
      router.replace("/planning/step-1");
    } else if (hilang) {
      clearIdGoalWizard();
      router.replace("/planning/step-1");
    }
  }, [idGoal, hilang, selesai, router]);

  return { idGoal: idGoal ?? null, goal };
}
