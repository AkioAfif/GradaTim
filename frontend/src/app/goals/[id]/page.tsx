"use client";

import { use, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { CalendarCheck, Sparkles } from "lucide-react";

import DashboardLayout from "../../../components/DashboardLayout";
import UserAvatar from "../../../components/UserAvatar";
import RencanaGoalTree from "../../../components/goal/RencanaGoalTree";
import HasilPenjadwalan from "../../../components/jadwal/HasilPenjadwalan";
import {
  cardClass,
  errorBoxClass,
  infoBoxClass,
  primaryButtonClass,
  secondaryButtonClass,
} from "../../../components/ui";
import { useCegahTutupTab, useDetikBerjalan } from "../../../components/useProsesLama";
import { ApiError, toApiError } from "../../../lib/api/client";
import { rinciMinggu } from "../../../lib/api/goals";
import { jadwalkanGoal } from "../../../lib/api/jadwal";
import { invalidateGoals, invalidateJadwal, useGoal } from "../../../lib/api/queries";
import type { GoalDetail, HasilPenjadwalanRead, RincianMingguRead } from "../../../lib/api/types";
import { setIdGoalWizard } from "../../../lib/planning";
import { progresTask, statusRinci } from "../../../lib/rencana";
import { formatTanggal, hariIniWib } from "../../../lib/waktu";

type HasilAksi =
  | { jenis: "rinci"; minggu: "ini" | "depan"; rincian: RincianMingguRead; jadwal: HasilPenjadwalanRead | null }
  | { jenis: "jadwal"; jadwal: HasilPenjadwalanRead };

type Aksi = { jenis: "rinci"; minggu: "ini" | "depan" } | { jenis: "jadwal" };

async function jalankanAksi(idGoal: number, aksi: Aksi): Promise<HasilAksi> {
  try {
    if (aksi.jenis === "jadwal") {
      return { jenis: "jadwal", jadwal: await jadwalkanGoal(idGoal) };
    }
    const rincian = await rinciMinggu(idGoal, aksi.minggu);
    // rinci-minggu tidak menjadwalkan; task minggu ini langsung dijadwalkan. Task minggu depan
    // baru bisa dijadwalkan saat minggunya tiba (backend melewatinya).
    const jadwal = aksi.minggu === "ini" ? await jadwalkanGoal(idGoal) : null;
    return { jenis: "rinci", minggu: aksi.minggu, rincian, jadwal };
  } catch (err) {
    throw toApiError(err);
  }
}

function RingkasanHasil({ hasil }: { hasil: HasilAksi }) {
  if (hasil.jenis === "jadwal") {
    return <HasilPenjadwalan sesiBaru={hasil.jadwal.sesi_baru} tidakMuat={hasil.jadwal.tidak_muat} />;
  }
  const { rincian, minggu, jadwal } = hasil;
  return (
    <div className="space-y-4">
      <p className={infoBoxClass}>
        {rincian.baru
          ? `${rincian.milestone.tasks.length} task dibuat untuk minggu ${minggu}.`
          : `Minggu ${minggu} sudah dirinci sebelumnya (${rincian.milestone.tasks.length} task).`}
        {minggu === "depan" && " Task-nya dijadwalkan otomatis saat kamu menekan Jadwalkan di minggu itu."}
      </p>
      {jadwal && <HasilPenjadwalan sesiBaru={jadwal.sesi_baru} tidakMuat={jadwal.tidak_muat} />}
    </div>
  );
}

function PanelMinggu({ goal }: { goal: GoalDetail }) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [hasil, setHasil] = useState<HasilAksi | null>(null);

  const aksi = useMutation<HasilAksi, ApiError, Aksi>({
    mutationFn: (a) => jalankanAksi(goal.id_goal, a),
    onSuccess: async (data) => {
      setHasil(data);
      await Promise.all([invalidateGoals(queryClient), invalidateJadwal(queryClient)]);
    },
    onError: () => {
      // rincian mungkin sudah tersimpan walau penjadwalan sesudahnya gagal → muat ulang rencana
      void invalidateGoals(queryClient);
    },
  });

  const memanggilAI = aksi.isPending && aksi.variables?.jenis === "rinci";
  const detik = useDetikBerjalan(memanggilAI);
  useCegahTutupTab(memanggilAI);

  if (goal.milestones.length === 0) {
    return (
      <div className={infoBoxClass}>
        <p>Goal ini belum punya rencana AI.</p>
        <button
          type="button"
          onClick={() => {
            setIdGoalWizard(goal.id_goal);
            router.push("/planning/step-3");
          }}
          className="mt-2 font-medium underline underline-offset-2"
        >
          Susun rencana dengan AI →
        </button>
      </div>
    );
  }

  const status = statusRinci(goal.milestones, hariIniWib());
  const sibuk = aksi.isPending;

  return (
    <div className="space-y-4">
      <div>
        <p className="text-xs font-semibold uppercase tracking-wide text-[#8B857B]">Minggu ini</p>
        {status.ini ? (
          <p className="mt-1 text-sm">
            <span className="font-medium">{status.ini.judul_milestone}</span>
            <span className="text-[#8B857B]">
              {" "}
              · {status.iniPerluDirinci ? "task belum dirinci" : `${status.ini.tasks.length} task`}
            </span>
          </p>
        ) : (
          <p className="mt-1 text-sm text-[#8B857B]">Tidak ada target untuk minggu ini (di luar rentang goal).</p>
        )}
      </div>

      <div className="flex flex-wrap gap-3">
        {status.iniPerluDirinci && (
          <button
            type="button"
            disabled={sibuk}
            onClick={() => aksi.mutate({ jenis: "rinci", minggu: "ini" })}
            className={`inline-flex items-center gap-2 ${primaryButtonClass}`}
          >
            <Sparkles size={16} />
            Rinci minggu ini
          </button>
        )}

        {status.depan && !status.depanSudahDirinci && (
          <span title={status.depanBolehSekarang ? undefined : "Task minggu depan baru bisa dirinci mulai hari Sabtu"}>
            <button
              type="button"
              disabled={sibuk || !status.depanBolehSekarang}
              onClick={() => aksi.mutate({ jenis: "rinci", minggu: "depan" })}
              className={`inline-flex items-center gap-2 ${secondaryButtonClass}`}
            >
              <Sparkles size={16} />
              Rinci minggu depan
            </button>
          </span>
        )}

        {status.ini && !status.iniPerluDirinci && (
          <button
            type="button"
            disabled={sibuk}
            onClick={() => aksi.mutate({ jenis: "jadwal" })}
            className={`inline-flex items-center gap-2 ${secondaryButtonClass}`}
          >
            <CalendarCheck size={16} />
            Jadwalkan task yang belum terjadwal
          </button>
        )}
      </div>

      {status.depan && !status.depanSudahDirinci && !status.depanBolehSekarang && (
        <p className="text-xs text-[#8B857B]">Task minggu depan bisa dirinci mulai hari Sabtu.</p>
      )}
      {status.depanSudahDirinci && <p className="text-xs text-[#8B857B]">Task minggu depan sudah dirinci.</p>}

      {memanggilAI && (
        <div role="status" className={`flex items-start gap-3 ${infoBoxClass}`}>
          <Sparkles size={18} className="mt-0.5 shrink-0 animate-pulse" />
          <p>
            AI sedang merinci task berdasarkan progresmu... ({detik} detik). Jangan tutup halaman ini.
          </p>
        </div>
      )}
      {aksi.isPending && !memanggilAI && <p className="text-sm text-[#8B857B]">Menjadwalkan...</p>}

      {aksi.isError && (
        <p role="alert" className={errorBoxClass}>
          {aksi.error.message}
        </p>
      )}

      {hasil && !aksi.isPending && <RingkasanHasil hasil={hasil} />}
    </div>
  );
}

export default function GoalDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const idGoal = Number(id);
  const idValid = Number.isInteger(idGoal) && idGoal > 0;
  const goal = useGoal(idValid ? idGoal : null);
  const tidakAda = !idValid || (goal.error instanceof ApiError && goal.error.status === 404);

  return (
    <DashboardLayout>
      <div className="mx-auto max-w-5xl">
        <header className="flex items-center justify-between border-b border-[#E9E0D4] pb-5">
          <p className="text-xs text-[#8B857B]">
            <Link href="/" className="hover:underline">
              Beranda
            </Link>{" "}
            / Goal
          </p>
          <UserAvatar />
        </header>

        {tidakAda ? (
          <div className={`mt-7 ${infoBoxClass}`}>
            Goal tidak ditemukan.{" "}
            <Link href="/" className="font-medium underline">
              Kembali ke beranda
            </Link>
          </div>
        ) : goal.isPending ? (
          <p className="mt-7 text-sm text-[#8B857B]">Memuat goal...</p>
        ) : goal.isError ? (
          <p role="alert" className={`mt-7 ${errorBoxClass}`}>
            {goal.error.message}
          </p>
        ) : (
          <>
            <section className="mt-7">
              <p className="text-xs font-bold tracking-[0.12em] text-[#506851]">GOAL</p>
              <h1 className="mt-3 text-3xl font-medium tracking-tight md:text-4xl">{goal.data.judul_goal}</h1>
              {goal.data.deskripsi && <p className="mt-3 text-sm text-[#64675E]">{goal.data.deskripsi}</p>}
              {goal.data.deadline && (
                <p className="mt-2 text-sm text-[#8B857B]">Deadline: {formatTanggal(goal.data.deadline)}</p>
              )}
              <ProgresBar goal={goal.data} />
            </section>

            <section className={`mt-7 ${cardClass}`}>
              <PanelMinggu goal={goal.data} />
            </section>

            <section className="mt-7">
              <h2 className="mb-4 text-lg font-semibold">Rencana</h2>
              <RencanaGoalTree goal={goal.data} />
            </section>
          </>
        )}
      </div>
    </DashboardLayout>
  );
}

function ProgresBar({ goal }: { goal: GoalDetail }) {
  const { selesai, total } = progresTask(goal.milestones);
  if (total === 0) return null;
  const persen = Math.round((selesai / total) * 100);
  return (
    <div className="mt-5 max-w-md">
      <div className="flex justify-between text-xs text-[#8B857B]">
        <span>
          {selesai} dari {total} task selesai
        </span>
        <span>{persen}%</span>
      </div>
      <div className="mt-1.5 h-2 overflow-hidden rounded-full bg-[#E5DFD3]">
        <div className="h-full rounded-full bg-[#82947B]" style={{ width: `${persen}%` }} />
      </div>
    </div>
  );
}
