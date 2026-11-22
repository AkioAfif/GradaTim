"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Pencil, Plus, Trash2 } from "lucide-react";

import DashboardLayout from "../../components/DashboardLayout";
import UserAvatar from "../../components/UserAvatar";
import { errorBoxClass } from "../../components/ui";
import { toApiError, type ApiError } from "../../lib/api/client";
import { invalidateJadwal, useGoals, useTasks } from "../../lib/api/queries";
import { updateTaskStatus } from "../../lib/api/tasks";
import type { TaskRead, TaskStatus } from "../../lib/api/types";
import { LABEL_STATUS_TASK, labelLevel } from "../../lib/label";
import { formatDurasi, formatTanggal } from "../../lib/waktu";

type Tab = "Tasks" | "Goals" | "Notes";

const BELUM_DIDUKUNG = "Belum didukung backend: task dibuat dari rencana AI";

const WARNA_STATUS: Record<TaskStatus, string> = {
  todo: "bg-[#F0E9DF] text-[#826049]",
  in_progress: "bg-[#FBF0DC] text-[#7A5A1E]",
  done: "bg-[#E2EBDD] text-[#506851]",
};

const selectClass =
  "rounded-lg border border-[#E5D9C9] bg-white px-3 py-2 text-sm outline-none focus:border-[#64765C]";

function BarisTask({ task }: { task: TaskRead }) {
  const queryClient = useQueryClient();
  const ubah = useMutation<TaskRead, ApiError, TaskStatus>({
    mutationFn: async (status) => {
      try {
        return await updateTaskStatus(task.id_task, status);
      } catch (err) {
        throw toApiError(err);
      }
    },
    // status task dipakai kalender (status_task) & rekomendasi mood
    onSettled: () => invalidateJadwal(queryClient),
  });

  const status = (ubah.isPending ? ubah.variables : task.status) as TaskStatus;

  return (
    <tr className="align-top hover:bg-[#FCF8F2]">
      <td className="px-4 py-4">
        <p className={`font-medium ${task.status === "done" ? "text-[#A49A8C] line-through" : ""}`}>
          {task.nama_task}
        </p>
        {task.deskripsi && <p className="mt-1 text-xs text-[#8B857B]">{task.deskripsi}</p>}
        <p className="mt-1 text-xs text-[#A49A8C]">
          {task.deadline
            ? `Deadline ${formatTanggal(task.deadline, { day: "numeric", month: "short" })}`
            : "Tanpa deadline"}
        </p>
        {ubah.isError && <p className="mt-1 text-xs text-[#8A3B2E]">{ubah.error.message}</p>}
      </td>
      <td className="px-4 py-4 text-[#64675E]">{formatDurasi(task.durasi_estimasi)}</td>
      <td className="px-4 py-4 text-[#64675E]">{labelLevel(task.tingkat_effort)}</td>
      <td className="px-4 py-4 text-[#64675E]">{labelLevel(task.tingkat_impact)}</td>
      <td className="px-4 py-4">
        <select
          value={status}
          disabled={ubah.isPending}
          onChange={(event) => ubah.mutate(event.target.value as TaskStatus)}
          aria-label={`Status ${task.nama_task}`}
          className={`rounded-full border-0 px-3 py-1.5 text-xs font-medium outline-none disabled:opacity-60 ${WARNA_STATUS[status] ?? ""}`}
        >
          {(Object.keys(LABEL_STATUS_TASK) as TaskStatus[]).map((s) => (
            <option key={s} value={s}>
              {LABEL_STATUS_TASK[s]}
            </option>
          ))}
        </select>
      </td>
      <td className="px-4 py-4">
        <div className="flex justify-end gap-2">
          <button
            type="button"
            disabled
            title={BELUM_DIDUKUNG}
            aria-label={`Edit ${task.nama_task} (belum didukung)`}
            className="cursor-not-allowed rounded-lg p-2 text-[#C9BFB2]"
          >
            <Pencil size={17} />
          </button>
          <button
            type="button"
            disabled
            title={BELUM_DIDUKUNG}
            aria-label={`Hapus ${task.nama_task} (belum didukung)`}
            className="cursor-not-allowed rounded-lg p-2 text-[#C9BFB2]"
          >
            <Trash2 size={17} />
          </button>
        </div>
      </td>
    </tr>
  );
}

function TabTasks() {
  const goals = useGoals();
  const [idGoal, setIdGoal] = useState<number | "">("");
  const [status, setStatus] = useState<TaskStatus | "">("");
  const filter = useMemo(
    () => ({
      ...(idGoal !== "" ? { id_goal: idGoal } : {}),
      ...(status !== "" ? { status } : {}),
    }),
    [idGoal, status]
  );
  const tasks = useTasks(filter);

  return (
    <>
      <div className="mt-6 flex flex-wrap items-center gap-3">
        <select
          value={idGoal}
          onChange={(event) => setIdGoal(event.target.value === "" ? "" : Number(event.target.value))}
          aria-label="Filter goal"
          className={selectClass}
        >
          <option value="">Semua goal</option>
          {(goals.data ?? []).map((g) => (
            <option key={g.id_goal} value={g.id_goal}>
              {g.judul_goal}
            </option>
          ))}
        </select>
        <select
          value={status}
          onChange={(event) => setStatus(event.target.value as TaskStatus | "")}
          aria-label="Filter status"
          className={selectClass}
        >
          <option value="">Semua status</option>
          {(Object.keys(LABEL_STATUS_TASK) as TaskStatus[]).map((s) => (
            <option key={s} value={s}>
              {LABEL_STATUS_TASK[s]}
            </option>
          ))}
        </select>
        {tasks.data && <span className="text-sm text-[#8B857B]">{tasks.data.length} task</span>}
      </div>

      {tasks.isError && (
        <p role="alert" className={`mt-4 ${errorBoxClass}`}>
          {tasks.error.message}
        </p>
      )}

      <div className="mt-4 overflow-x-auto rounded-xl border border-[#E7DBCC] bg-white">
        <table className="w-full min-w-[720px] border-collapse text-left text-sm">
          <thead className="bg-[#F1EADF]">
            <tr>
              <th className="px-4 py-4 font-semibold">Task</th>
              <th className="px-4 py-4 font-semibold">Est. Time</th>
              <th className="px-4 py-4 font-semibold">Effort</th>
              <th className="px-4 py-4 font-semibold">Impact</th>
              <th className="px-4 py-4 font-semibold">Status</th>
              <th className="px-4 py-4 text-right font-semibold">Aksi</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#EEE6DA]">
            {tasks.isPending ? (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-[#8B857B]">
                  Memuat...
                </td>
              </tr>
            ) : (tasks.data ?? []).length === 0 ? (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-[#8B857B]">
                  {idGoal !== "" || status !== "" ? (
                    "Tidak ada task yang cocok dengan filter."
                  ) : (
                    <>
                      Belum ada task. Task dibuat oleh AI dari goal-mu —{" "}
                      <Link href="/planning/step-1" className="font-medium text-[#506851] underline">
                        buat rencana baru
                      </Link>
                      .
                    </>
                  )}
                </td>
              </tr>
            ) : (
              (tasks.data ?? []).map((task) => <BarisTask key={task.id_task} task={task} />)
            )}
          </tbody>
        </table>
      </div>

      <p className="mt-3 text-xs text-[#8B857B]">
        Status juga diperbarui otomatis saat sesi task dikonfirmasi di kalender; perubahan manual di sini akan
        dihitung ulang begitu ada sesi task itu yang dikonfirmasi.
      </p>
    </>
  );
}

function TabGoals() {
  const goals = useGoals();
  if (goals.isPending) return <p className="mt-6 text-sm text-[#8B857B]">Memuat...</p>;
  if (goals.isError) {
    return (
      <p role="alert" className={`mt-6 ${errorBoxClass}`}>
        {goals.error.message}
      </p>
    );
  }
  if (goals.data.length === 0) {
    return <p className="mt-6 text-sm text-[#8B857B]">Belum ada goal.</p>;
  }
  return (
    <ul className="mt-6 divide-y divide-[#EEE6DA] rounded-xl border border-[#E7DBCC] bg-white">
      {goals.data.map((g) => (
        <li key={g.id_goal}>
          <Link
            href={`/goals/${g.id_goal}`}
            className="flex items-center justify-between gap-4 px-5 py-4 hover:bg-[#FCF8F2]"
          >
            <span className="font-medium">{g.judul_goal}</span>
            <span className="shrink-0 text-xs text-[#8B857B]">
              {g.deadline ? `Deadline ${formatTanggal(g.deadline, { day: "numeric", month: "short", year: "numeric" })}` : ""}
            </span>
          </Link>
        </li>
      ))}
    </ul>
  );
}

export default function TasksPage() {
  const [activeTab, setActiveTab] = useState<Tab>("Tasks");

  return (
    <DashboardLayout>
      <div className="mx-auto max-w-6xl">
        {/* TOP BAR */}
        <header className="flex items-center justify-between border-b border-[#E9E0D4] pb-5">
          <p className="text-xs text-[#8B857B]">Task Management</p>
          <UserAvatar />
        </header>

        {/* PAGE HEADING */}
        <section className="mt-7">
          <p className="text-xs font-bold tracking-[0.12em] text-[#506851]">TUGAS</p>
          <h1 className="mt-3 text-3xl font-medium tracking-tight md:text-4xl">Kelola Tugas &amp; Target</h1>
          <p className="mt-3 text-sm text-[#8B857B]">Prioritaskan aktivitas yang mendukung tujuanmu.</p>
        </section>

        {/* TABS AND ADD BUTTON */}
        <section className="mt-7 flex flex-wrap items-center justify-between gap-4">
          <div className="flex gap-3" role="tablist">
            {(["Tasks", "Goals", "Notes"] as Tab[]).map((tab) => (
              <button
                key={tab}
                type="button"
                role="tab"
                aria-selected={activeTab === tab}
                onClick={() => setActiveTab(tab)}
                className={`rounded-full px-5 py-2 text-sm font-medium ${
                  activeTab === tab
                    ? "bg-[#F0C4A4] text-[#45382E]"
                    : "bg-[#ECE9E1] text-[#57564F] hover:bg-[#E2DDD3]"
                }`}
              >
                {tab}
              </button>
            ))}
          </div>

          <button
            type="button"
            disabled
            title={BELUM_DIDUKUNG}
            className="inline-flex cursor-not-allowed items-center gap-2 rounded-lg bg-[#D8CBBE] px-5 py-3 text-sm font-medium text-white"
          >
            <Plus size={16} />
            Tambah Tugas
          </button>
        </section>

        {activeTab === "Tasks" && <TabTasks />}
        {activeTab === "Goals" && <TabGoals />}
        {activeTab === "Notes" && (
          <div className="mt-6 rounded-xl border border-dashed border-[#D8CBB9] p-8 text-center text-sm text-[#8B857B]">
            Fitur Notes akan diimplementasikan pada tahap berikutnya.
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}
