
"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import DashboardLayout from "../../../components/DashboardLayout";
import { useTasks } from "../../../context/TaskContext";

export default function PlanningStep7() {
  const router = useRouter();
  const { tasks } = useTasks();

  const [reflection, setReflection] = useState("");
  const [saved, setSaved] = useState(false);

  const completedTasks = tasks.filter(
    (task) => task.completed
  ).length;

  const totalTasks = tasks.length;

  const overallProgress =
    totalTasks > 0
      ? Math.round((completedTasks / totalTasks) * 100)
      : 0;

  const currentTask = tasks.find(
    (task) => !task.completed
  );

  useEffect(() => {
    try {
      const stored = localStorage.getItem(
        "gradatim-reflection"
      );

      if (stored) {
        setReflection(stored);
      }
    } catch (error) {
      console.error("Gagal membaca refleksi:", error);
    }
  }, []);

  
function handleSave() {
  try {
    // 1. Simpan refleksi ke browser
    localStorage.setItem(
      "gradatim-reflection",
      reflection
    );

    // 2. Tandai draft planning sebagai selesai
    const savedDraft = sessionStorage.getItem(
      "gradatim-planning-draft"
    );

    if (savedDraft) {
      const draft = JSON.parse(savedDraft);

      sessionStorage.setItem(
        "gradatim-planning-draft",
        JSON.stringify({
          ...draft,
          wizardCompleted: true,
        })
      );
    }

    // 3. Kembali ke Dashboard
    router.push("/");
  } catch (error) {
    console.error("Gagal menyimpan refleksi:", error);
    alert("Refleksi gagal disimpan. Silakan coba lagi.");
  }
}


  return (
    <DashboardLayout>
      <div className="mx-auto max-w-5xl">
        {/* HEADER */}
        <header className="flex items-center justify-between border-b border-[#E9E0D4] pb-5">
          <p className="text-xs text-[#8B857B]">
            Progress Tracking
          </p>

          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-[#D7B99B] text-sm text-white">
            A
          </div>
        </header>

        {/* TITLE */}
        <section className="mt-7">
          <p className="text-xs font-bold tracking-[0.12em] text-[#506851]">
            LANGKAH 7 DARI 7
          </p>

          <h1 className="mt-3 text-3xl font-medium tracking-tight md:text-4xl">
            Progress &amp; Refleksi
          </h1>

          <p className="mt-3 text-sm text-[#8B857B]">
            Lihat perkembanganmu dan evaluasi apa yang bisa diperbaiki.
          </p>
        </section>

        {/* PROGRESS CARD */}
        <section className="mt-7 rounded-xl border border-[#E7DBCC] bg-[#FFFCF7] p-5 sm:p-7">
          {/* OVERALL PROGRESS */}
          <div>
            <div className="flex items-center justify-between gap-3">
              <h2 className="text-sm font-semibold">
                Overall Progress
              </h2>

              <span className="text-sm font-semibold">
                {overallProgress}%
              </span>
            </div>

            <div className="mt-3 h-3 overflow-hidden rounded-full bg-[#E8E2D7]">
              <div
                className="h-full rounded-full bg-[#82947B] transition-all"
                style={{
                  width: `${overallProgress}%`,
                }}
              />
            </div>

            <p className="mt-3 text-xs text-[#8B857B]">
              {completedTasks} dari {totalTasks} tugas selesai
            </p>
          </div>

          <div className="my-6 border-t border-[#E9E0D4]" />

          {/* CURRENT TASK */}
          <div>
            <h2 className="text-sm font-semibold">
              Current Task
            </h2>

            <div className="mt-3 rounded-lg border border-[#E5D9C9] bg-white px-4 py-3 text-sm">
              {currentTask
                ? currentTask.title
                : totalTasks === 0
                ? "Belum ada tugas."
                : "Semua tugas sudah selesai! 🎉"}
            </div>
          </div>

          {/* BUILD PROGRESS */}
          <div className="mt-7">
            <div className="flex items-center justify-between gap-3">
              <h2 className="text-sm font-semibold">
                Build Progress
              </h2>

              <span className="text-sm font-semibold">
                {overallProgress}%
              </span>
            </div>

            <div className="mt-3 h-3 overflow-hidden rounded-full bg-[#E8E2D7]">
              <div
                className="h-full rounded-full bg-[#82947B] transition-all"
                style={{
                  width: `${overallProgress}%`,
                }}
              />
            </div>

            <p className="mt-2 text-xs text-[#8B857B]">
              Sementara menggunakan progres penyelesaian tugas.
            </p>
          </div>

          {/* REFLECTION */}
          <div className="mt-7">
            <label
              htmlFor="reflection"
              className="mb-3 block text-sm font-semibold"
            >
              Reflection
            </label>

            <textarea
              id="reflection"
              rows={5}
              value={reflection}
              onChange={(event) => {
                setReflection(event.target.value);
                setSaved(false);
              }}
              placeholder="Apa yang sudah berjalan baik? Apa yang perlu diperbaiki?"
              className="w-full resize-y rounded-lg border border-[#E5D9C9] bg-white px-4 py-3 text-sm outline-none focus:border-[#64765C]"
            />

            {saved && (
              <p
                role="status"
                className="mt-2 text-xs font-medium text-[#506851]"
              >
                Refleksi berhasil disimpan di browser.
              </p>
            )}
          </div>
        </section>

        {/* NAVIGATION */}
        <div className="mt-6 flex flex-wrap items-center justify-between gap-4">
          <Link
            href="/tasks"
            className="rounded-lg border border-[#DDD2C3] bg-[#ECE9E1] px-5 py-3 text-sm font-medium hover:bg-[#E2DDD3]"
          >
            ← Kembali
          </Link>

          <button
  type="button"
  onClick={handleSave}
  className="rounded-lg bg-[#826049] px-6 py-3 text-sm font-medium text-white hover:bg-[#6D4D38]"
>
  Simpan &amp; Selesai →
</button>
        </div>

        <p className="mt-5 text-xs text-[#9A8F81]">
          Progres dihitung dari tugas yang tersimpan di browser.
          Data sprint AI belum terintegrasi.
        </p>
      </div>
    </DashboardLayout>
  );
}
