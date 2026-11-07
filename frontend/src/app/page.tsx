
"use client";

import { useState } from "react";
import {
  Bell,
  CalendarDays,
  CheckCircle2,
  Plus,
  Search,
} from "lucide-react";

import DashboardLayout from "../components/DashboardLayout";
import { useTasks } from "../context/TaskContext";

export default function Home() {
  const { tasks, addTask, toggleTask } = useTasks();
  const [newTask, setNewTask] = useState("");
  const [search, setSearch] = useState("");

  const completed = tasks.filter(
    (task) => task.completed
  ).length;

  const progress = tasks.length
    ? Math.round((completed / tasks.length) * 100)
    : 0;

  const filteredTasks = tasks.filter((task) =>
    task.title.toLowerCase().includes(search.toLowerCase())
  );

  function handleAddTask() {
    if (!newTask.trim()) return;

    addTask({
      title: newTask.trim(),
      completed: false,
      priority: "Medium",
      deadline: "",
    });

    setNewTask("");
  }

  return (
    <DashboardLayout>
      {/* HEADER */}
      <header className="flex flex-wrap items-center justify-between gap-5">
        <div>
          <p className="text-sm text-[#8A7A69]">
            Personal Productivity Planner
          </p>

          <h1 className="mt-2 font-serif text-4xl font-semibold">
            Dashboard
          </h1>
        </div>

        <div className="flex items-center gap-4">
          <div className="hidden items-center gap-2 rounded-xl border border-[#E8DED1] bg-white px-4 py-3 md:flex">
            <Search size={17} className="text-[#8A7A69]" />

            <input
              value={search}
              onChange={(event) =>
                setSearch(event.target.value)
              }
              aria-label="Cari tugas"
              placeholder="Cari tugas..."
              className="w-40 bg-transparent text-sm outline-none"
            />
          </div>

          <Bell size={21} className="text-[#64765C]" />

          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-[#D6B99B] font-semibold text-white">
            A
          </div>
        </div>
      </header>

      {/* WELCOME */}
      <section className="mt-10">
        <h2 className="font-serif text-3xl font-semibold">
          Selamat datang di GradaTim!
        </h2>

        <p className="mt-2 text-[#817769]">
          Kelola tugas, atur jadwal, dan capai targetmu
          dengan lebih terarah.
        </p>
      </section>

      {/* PROGRESS */}
      <section className="mt-8 rounded-2xl border border-[#E9DED0] bg-white p-7 shadow-sm">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold">
              Progress Hari Ini
            </h3>

            <p className="mt-1 text-sm text-[#8A7A69]">
              {completed} dari {tasks.length} tugas selesai
            </p>
          </div>

          <span className="text-xl font-bold text-[#64765C]">
            {progress}%
          </span>
        </div>

        <div className="mt-5 h-3 overflow-hidden rounded-full bg-[#EEE8DE]">
          <div
            className="h-full rounded-full bg-[#8D9B80] transition-all"
            style={{ width: `${progress}%` }}
          />
        </div>
      </section>

      {/* DASHBOARD CARDS */}
      <section className="mt-8 grid gap-6 lg:grid-cols-2">
        {/* TODAY ACTION LIST */}
        <div className="rounded-2xl border border-[#E9DED0] bg-[#FFF9F0] p-7 shadow-sm">
          <div className="mb-6 flex items-center gap-3">
            <CheckCircle2
              size={24}
              className="text-[#826049]"
            />

            <h3 className="text-xl font-semibold">
              Today Action List
            </h3>
          </div>

          <div className="space-y-4">
            {filteredTasks.length === 0 ? (
              <p className="text-sm text-[#817769]">
                Tidak ada tugas yang ditemukan.
              </p>
            ) : (
              filteredTasks.map((task) => (
                <label
                  key={task.id}
                  className="flex cursor-pointer items-center gap-3"
                >
                  <input
                    type="checkbox"
                    checked={task.completed}
                    onChange={() => toggleTask(task.id)}
                    className="h-4 w-4 accent-[#64765C]"
                  />

                  <span
                    className={`text-sm ${
                      task.completed
                        ? "text-[#99948A] line-through"
                        : "text-[#45453D]"
                    }`}
                  >
                    {task.title}
                  </span>
                </label>
              ))
            )}
          </div>

          {/* ADD TASK */}
          <div className="mt-7 flex gap-2">
            <input
              value={newTask}
              onChange={(event) =>
                setNewTask(event.target.value)
              }
              onKeyDown={(event) => {
                if (event.key === "Enter") {
                  handleAddTask();
                }
              }}
              placeholder="Tambah tugas baru..."
              className="min-w-0 flex-1 rounded-lg border border-[#E5D9C9] bg-white px-3 py-2 text-sm outline-none focus:border-[#64765C]"
            />

            <button
              type="button"
              onClick={handleAddTask}
              aria-label="Tambah tugas"
              className="rounded-lg bg-[#826049] px-4 text-white hover:bg-[#6D4D38]"
            >
              <Plus size={18} />
            </button>
          </div>
        </div>

        {/* WEEKLY VIEW */}
        <div className="rounded-2xl border border-[#E9DED0] bg-[#FFF9F0] p-7 shadow-sm">
          <div className="mb-6 flex items-center gap-3">
            <CalendarDays
              size={24}
              className="text-[#64765C]"
            />

            <h3 className="text-xl font-semibold">
              Weekly View
            </h3>
          </div>

          <p className="text-sm leading-7 text-[#817769]">
            Pantau aktivitas dan rencana mingguanmu
            agar setiap target bisa diselesaikan tepat waktu.
          </p>

          <div className="mt-8 rounded-xl bg-[#F1E9DC] p-5">
            <p className="text-sm font-semibold">
              Ringkasan Minggu Ini
            </p>

            <p className="mt-2 text-sm text-[#817769]">
              Mulai dari langkah kecil dan pertahankan
              konsistensimu setiap hari.
            </p>
          </div>

          <button
            type="button"
            disabled
            title="Halaman kalender belum dibuat"
            className="mt-7 cursor-not-allowed rounded-xl bg-[#826049] px-6 py-3 text-sm font-medium text-white opacity-60"
          >
            Lihat Mingguan
          </button>
        </div>
      </section>

      {/* FOOTER */}
      <footer className="mt-10 text-center text-xs text-[#A49A8C]">
        GradaTim — Plan, Focus, Achieve
      </footer>
    </DashboardLayout>
  );
}
