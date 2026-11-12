
"use client";

import { useState } from "react";
import Link from "next/link";
import { Bell, Plus, Search } from "lucide-react";

import DashboardLayout from "../components/DashboardLayout";
import { useTasks } from "../context/TaskContext";

function dateKey(date: Date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");

  return `${year}-${month}-${day}`;
}

export default function Home() {
  const { tasks, addTask, toggleTask } = useTasks();

  const [newTask, setNewTask] = useState("");
  const [search, setSearch] = useState("");
  const [showAddTask, setShowAddTask] = useState(false);

  const completed = tasks.filter(
    (task) => task.completed
  ).length;

  const progress = tasks.length
    ? Math.round((completed / tasks.length) * 100)
    : 0;

  const filteredTasks = tasks.filter((task) =>
    task.title.toLowerCase().includes(search.toLowerCase())
  );

  const today = new Date();

  const weeklyDays = Array.from({ length: 7 }, (_, index) => {
    const day = new Date(today);
    const mondayOffset = (today.getDay() + 6) % 7;

    day.setDate(today.getDate() - mondayOffset + index);

    return {
      key: dateKey(day),
      label: day.toLocaleDateString("id-ID", {
        weekday: "long",
      }),
    };
  });

  const weeklySummary = weeklyDays
    .map((day) => ({
      ...day,
      count: tasks.filter(
        (task) => task.deadline === day.key
      ).length,
    }))
    .filter((day) => day.count > 0);

  function handleAddTask() {
    if (!newTask.trim()) return;

    addTask({
      title: newTask.trim(),
      completed: false,
      priority: "Medium",
      deadline: "",
    });

    setNewTask("");
    setShowAddTask(false);
  }

  return (
    <DashboardLayout>
      <div className="mx-auto max-w-5xl">
        {/* TOP BAR */}
        <header className="flex items-center justify-between gap-4 border-b border-[#E9E0D4] pb-5">
          <div className="flex min-w-0 items-center gap-2 rounded-lg border border-[#E5DCD0] bg-white px-3 py-2">
            <Search
              size={15}
              className="shrink-0 text-[#8B857B]"
            />

            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Cari tugas, kategori, atau catatan..."
              aria-label="Cari tugas"
              className="min-w-0 w-48 bg-transparent text-xs outline-none sm:w-64"
            />
          </div>

          <div className="flex items-center gap-5">
            <Bell size={17} className="text-[#8B857B]" />

            <div className="flex h-9 w-9 items-center justify-center rounded-full bg-[#D7B99B] text-sm font-medium text-white">
              A
            </div>
          </div>
        </header>

        {/* WELCOME + CREATE PLAN BUTTON */}
        <section className="mt-7">
          <div className="flex flex-col gap-5 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="text-xs font-bold tracking-[0.12em] text-[#506851]">
                DASHBOARD
              </p>

              <h1 className="mt-3 text-3xl font-medium tracking-tight text-[#30312B] md:text-4xl">
                Selamat datang kembali!
              </h1>

              <p className="mt-3 text-sm text-[#8B857B]">
                Yuk, wujudkan targetmu hari ini, satu langkah kecil
                setiap waktu.
              </p>
            </div>

            <Link
              href="/planning/step-1"
              className="inline-flex shrink-0 items-center justify-center gap-2 self-start rounded-xl bg-[#826049] px-5 py-3 text-sm font-medium text-white transition-colors hover:bg-[#6D4D38]"
            >
              <Plus size={18} />
              Buat Rencana Baru
            </Link>
          </div>
        </section>

        {/* STATISTICS */}
        <section className="mt-7 grid gap-4 md:grid-cols-2">
          <div className="rounded-xl bg-[#F3EADD] p-6">
            <p className="text-sm text-[#8B857B]">
              Progress Mingguan
            </p>

            <p className="mt-3 text-3xl font-bold text-[#506851]">
              {progress}%
            </p>

            <div className="mt-3 h-3 overflow-hidden rounded-full bg-[#EAE3D9]">
              <div
                className="h-full rounded-full bg-[#82947B] transition-all"
                style={{ width: `${progress}%` }}
              />
            </div>

            <p className="mt-3 text-xs text-[#8B857B]">
              Progress seluruh tugas yang tercatat
            </p>
          </div>

          <div className="rounded-xl bg-[#F3EADD] p-6">
            <p className="text-sm text-[#8B857B]">
              Target Tercapai
            </p>

            <p className="mt-3 text-3xl font-bold text-[#506851]">
              {completed} dari {tasks.length}
            </p>

            <p className="mt-3 text-xs text-[#8B857B]">
              Terus pertahankan konsistensimu!
            </p>
          </div>
        </section>

        {/* MAIN CARDS */}
        <section className="mt-4 grid gap-4 md:grid-cols-2">
          {/* TODAY ACTION LIST */}
          <div className="rounded-xl border border-[#E7DBCC] bg-[#F7EEE3] p-5">
            <h2 className="text-base font-bold">
              Today Action List
            </h2>

            <div className="mt-5 divide-y divide-[#EBE2D6]">
              {filteredTasks.length === 0 ? (
                <p className="py-4 text-sm text-[#8B857B]">
                  Tidak ada tugas yang ditemukan.
                </p>
              ) : (
                filteredTasks.slice(0, 5).map((task) => (
                  <label
                    key={task.id}
                    className="flex cursor-pointer items-center gap-3 py-3"
                  >
                    <input
                      type="checkbox"
                      checked={task.completed}
                      onChange={() => toggleTask(task.id)}
                      className="h-4 w-4 accent-[#82947B]"
                    />

                    <span
                      className={`text-sm ${
                        task.completed
                          ? "text-[#A49A8C] line-through"
                          : "text-[#45453D]"
                      }`}
                    >
                      {task.title}
                    </span>
                  </label>
                ))
              )}
            </div>

            {showAddTask ? (
              <div className="mt-4 flex gap-2">
                <input
                  autoFocus
                  value={newTask}
                  onChange={(event) =>
                    setNewTask(event.target.value)
                  }
                  onKeyDown={(event) => {
                    if (event.key === "Enter") {
                      handleAddTask();
                    }
                  }}
                  placeholder="Nama tugas baru..."
                  className="min-w-0 flex-1 rounded-lg border border-[#E5D9C9] bg-white px-3 py-2 text-sm outline-none"
                />

                <button
                  type="button"
                  onClick={handleAddTask}
                  aria-label="Simpan tugas"
                  className="rounded-lg bg-[#826049] px-3 text-white"
                >
                  <Plus size={17} />
                </button>
              </div>
            ) : (
              <button
                type="button"
                onClick={() => setShowAddTask(true)}
                className="mt-4 text-sm text-[#8B857B] hover:text-[#826049]"
              >
                + Tambah tugas
              </button>
            )}
          </div>

          {/* WEEKLY VIEW */}
          <div className="rounded-xl border border-[#E7DBCC] bg-[#F7EEE3] p-5">
            <h2 className="text-base font-bold">
              Weekly View
            </h2>

            <p className="mt-3 text-sm text-[#8B857B]">
              Lihat aktivitas dan jadwal mingguanmu.
            </p>

            <div className="mt-5 space-y-2">
              {weeklySummary.length === 0 ? (
                <p className="rounded-lg border border-[#E7DBCC] bg-[#FBF6EE] p-4 text-sm text-[#8B857B]">
                  Belum ada tugas dengan deadline minggu ini.
                </p>
              ) : (
                weeklySummary.map((day) => (
                  <div
                    key={day.key}
                    className="flex items-center justify-between rounded-lg border border-[#E7DBCC] bg-[#FBF6EE] px-4 py-4"
                  >
                    <span className="text-sm">
                      {day.label}
                    </span>

                    <span className="text-sm">
                      {day.count} tugas
                    </span>
                  </div>
                ))
              )}
            </div>

            <Link
              href="/calendar"
              className="mt-5 inline-flex rounded-lg bg-[#826049] px-5 py-3 text-sm font-medium text-white hover:bg-[#6D4D38]"
            >
              Lihat Mingguan →
            </Link>
          </div>
        </section>
      </div>
    </DashboardLayout>
  );
}
