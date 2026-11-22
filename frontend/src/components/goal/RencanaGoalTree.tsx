"use client";

import type { ReactNode } from "react";

import type { GoalDetail, MilestoneRead, TaskRead } from "../../lib/api/types";
import { labelLevel, labelStatusTask } from "../../lib/label";
import { mingguanPada, susunPohon } from "../../lib/rencana";
import { awalMinggu, formatDurasi, formatTanggal, formatTanggalPendek, hariIniWib, tanggalDari } from "../../lib/waktu";

function TaskItem({ task, namaTask }: { task: TaskRead; namaTask: Map<number, string> }) {
  const prasyarat = task.prasyarat.map((id) => namaTask.get(id) ?? `Task #${id}`);
  return (
    <li className="py-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <p className={`text-sm font-medium ${task.status === "done" ? "text-[#A49A8C] line-through" : ""}`}>
          {task.nama_task}
        </p>
        {task.status !== "todo" && (
          <span className="rounded-full bg-[#E2EBDD] px-2.5 py-0.5 text-xs text-[#506851]">
            {labelStatusTask(task.status)}
          </span>
        )}
      </div>
      {task.deskripsi && <p className="mt-1 text-xs text-[#64675E]">{task.deskripsi}</p>}
      <p className="mt-1.5 flex flex-wrap gap-x-4 gap-y-1 text-xs text-[#8B857B]">
        <span>⏱ {formatDurasi(task.durasi_estimasi)}</span>
        <span>Effort: {labelLevel(task.tingkat_effort)}</span>
        <span>Impact: {labelLevel(task.tingkat_impact)}</span>
      </p>
      {prasyarat.length > 0 && (
        <p className="mt-1 text-xs text-[#8B857B]">Setelah: {prasyarat.join(", ")}</p>
      )}
    </li>
  );
}

function MingguCard({
  minggu,
  mingguIni,
  namaTask,
  aksi,
}: {
  minggu: MilestoneRead;
  mingguIni: boolean;
  namaTask: Map<number, string>;
  aksi?: ReactNode;
}) {
  const akhir = minggu.deadline ? tanggalDari(minggu.deadline) : null;
  const sudahTiba = akhir !== null && awalMinggu(akhir) <= awalMinggu(hariIniWib());

  return (
    <div
      className={`rounded-lg border bg-white p-4 ${
        mingguIni ? "border-[#82947B] ring-1 ring-[#82947B]" : "border-[#EBE2D6]"
      }`}
    >
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <p className="text-sm font-semibold">
            Minggu {minggu.urutan}: {minggu.judul_milestone}
          </p>
          {akhir && <p className="mt-0.5 text-xs text-[#8B857B]">s/d {formatTanggalPendek(akhir)}</p>}
        </div>
        {mingguIni && (
          <span className="rounded-full bg-[#506851] px-2.5 py-0.5 text-xs font-medium text-white">Minggu ini</span>
        )}
      </div>
      {minggu.deskripsi && <p className="mt-2 text-xs text-[#64675E]">{minggu.deskripsi}</p>}

      {minggu.tasks.length > 0 ? (
        <ul className="mt-2 divide-y divide-[#F0E9DF]">
          {minggu.tasks.map((task) => (
            <TaskItem key={task.id_task} task={task} namaTask={namaTask} />
          ))}
        </ul>
      ) : (
        <p className="mt-3 text-xs italic text-[#8B857B]">
          {sudahTiba ? "Task minggu ini belum dirinci." : "Task dirinci saat minggunya tiba."}
        </p>
      )}

      {aksi && <div className="mt-3">{aksi}</div>}
    </div>
  );
}

/**
 * Rencana goal: target bulanan → mingguan → task. `aksiMinggu` (opsional) merender tombol di bawah
 * kartu minggu tertentu (mis. "Rinci minggu ini" di halaman goal).
 */
export default function RencanaGoalTree({
  goal,
  aksiMinggu,
}: {
  goal: GoalDetail;
  aksiMinggu?: (minggu: MilestoneRead, mingguIni: boolean) => ReactNode;
}) {
  const pohon = susunPohon(goal.milestones);
  const idMingguIni = mingguanPada(goal.milestones, hariIniWib())?.id_milestone ?? null;
  const namaTask = new Map(goal.milestones.flatMap((m) => m.tasks.map((t) => [t.id_task, t.nama_task] as const)));

  if (goal.milestones.length === 0) {
    return <p className="text-sm text-[#8B857B]">Goal ini belum punya rencana.</p>;
  }

  return (
    <div className="space-y-4">
      {pohon.bulan.map(({ bulan, minggu }, indeks) => {
        const berisiMingguIni = minggu.some((m) => m.id_milestone === idMingguIni);
        return (
          <details
            key={bulan.id_milestone}
            open={berisiMingguIni || (idMingguIni === null && indeks === 0)}
            className="group rounded-xl border border-[#E7DBCC] bg-[#F7EEE3] p-4 sm:p-5"
          >
            <summary className="flex cursor-pointer list-none items-start justify-between gap-3">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-[#8B857B]">Bulan {bulan.urutan}</p>
                <p className="mt-1 font-semibold">{bulan.judul_milestone}</p>
                {bulan.deadline && (
                  <p className="mt-0.5 text-xs text-[#8B857B]">Sampai {formatTanggal(bulan.deadline)}</p>
                )}
              </div>
              <span className="mt-1 text-sm text-[#8B857B] transition group-open:rotate-90">▸</span>
            </summary>
            {bulan.deskripsi && <p className="mt-3 text-sm text-[#64675E]">{bulan.deskripsi}</p>}
            <div className="mt-4 space-y-3">
              {minggu.map((m) => {
                const mingguIni = m.id_milestone === idMingguIni;
                return (
                  <MingguCard
                    key={m.id_milestone}
                    minggu={m}
                    mingguIni={mingguIni}
                    namaTask={namaTask}
                    aksi={aksiMinggu?.(m, mingguIni)}
                  />
                );
              })}
            </div>
          </details>
        );
      })}

      {pohon.lainnya.map((m) => (
        <MingguCard key={m.id_milestone} minggu={m} mingguIni={false} namaTask={namaTask} aksi={aksiMinggu?.(m, false)} />
      ))}
    </div>
  );
}
