
"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import DashboardLayout from "../../../components/DashboardLayout";

export default function PlanningStep4() {
  const router = useRouter();

  const [activityLevel, setActivityLevel] = useState(55);
  const [note, setNote] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    try {
      const saved = sessionStorage.getItem(
        "gradatim-planning-draft"
      );

      if (!saved) return;

      const draft = JSON.parse(saved);

      if (typeof draft.activityLevel === "number") {
        setActivityLevel(draft.activityLevel);
      }

      if (typeof draft.dailyNote === "string") {
        setNote(draft.dailyNote);
      }
    } catch (error) {
      console.error("Gagal membaca draft:", error);
    }
  }, []);

  function handleNext() {
    try {
      const saved = sessionStorage.getItem(
        "gradatim-planning-draft"
      );

      if (!saved) {
        setError(
          "Draft belum ditemukan. Isi Langkah 1 terlebih dahulu."
        );
        return;
      }

      const draft = JSON.parse(saved);

      sessionStorage.setItem(
        "gradatim-planning-draft",
        JSON.stringify({
          ...draft,
          activityLevel,
          dailyNote: note,
        })
      );

      // Langkah 5 akan dibuat setelah halaman ini diuji.
      router.push("/planning/step-5");
    } catch (error) {
      console.error("Gagal menyimpan perencanaan harian:", error);
      setError("Terjadi kesalahan saat menyimpan data.");
    }
  }

  const activityLabel =
    activityLevel <= 33
      ? "Lebih santai"
      : activityLevel <= 66
      ? "Seimbang"
      : "Lebih produktif";

  return (
    <DashboardLayout>
      <div className="mx-auto max-w-5xl">
        {/* HEADER */}
        <header className="flex items-center justify-between border-b border-[#E9E0D4] pb-5">
          <p className="text-xs text-[#8B857B]">
            Daily Planning
          </p>

          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-[#D7B99B] text-sm text-white">
            A
          </div>
        </header>

        {/* TITLE */}
        <section className="mt-7">
          <p className="text-xs font-bold tracking-[0.12em] text-[#506851]">
            LANGKAH 4 DARI 7
          </p>

          <h1 className="mt-3 text-3xl font-medium tracking-tight md:text-4xl">
            Rencanakan Harimu
          </h1>

          <p className="mt-3 text-sm text-[#8B857B]">
            Are you planning something today? Write down your plan.
          </p>
        </section>

        {/* FORM */}
        <section className="mt-7 rounded-xl border border-[#E7DBCC] bg-[#FFFCF7] p-5 sm:p-7">
          <div>
            <label
              htmlFor="activity-level"
              className="block text-sm font-semibold"
            >
              Seberapa padat harimu?
            </label>

            <input
              id="activity-level"
              type="range"
              min="0"
              max="100"
              step="1"
              value={activityLevel}
              onChange={(event) =>
                setActivityLevel(Number(event.target.value))
              }
              aria-valuetext={activityLabel}
              className="mt-6 w-full cursor-pointer accent-[#826049]"
            />

            <div className="mt-2 flex justify-between gap-3 text-xs text-[#57564F]">
              <span>Lebih santai</span>
              <span>Seimbang</span>
              <span>Lebih produktif</span>
            </div>

            <p className="mt-4 text-sm text-[#506851]">
              Pilihanmu: <strong>{activityLabel}</strong>
            </p>
          </div>

          <div className="mt-8">
            <label
              htmlFor="daily-note"
              className="mb-3 block text-sm font-semibold"
            >
              Optional Note
            </label>

            <textarea
              id="daily-note"
              rows={5}
              value={note}
              onChange={(event) => setNote(event.target.value)}
              placeholder="Tulis catatan tambahan di sini..."
              className="w-full resize-y rounded-lg border border-[#E5D9C9] bg-white px-4 py-3 text-sm outline-none focus:border-[#64765C]"
            />
          </div>
        </section>

        {error && (
          <p role="alert" className="mt-4 text-sm text-red-700">
            {error}
          </p>
        )}

        {/* NAVIGATION */}
        <div className="mt-5 flex items-center justify-between gap-4">
          <Link
            href="/planning/step-3"
            className="rounded-lg border border-[#DDD2C3] bg-[#ECE9E1] px-5 py-3 text-sm font-medium"
          >
            ← Kembali
          </Link>

          <button
            type="button"
            onClick={handleNext}
            className="rounded-lg bg-[#826049] px-6 py-3 text-sm font-medium text-white hover:bg-[#6D4D38]"
          >
            Lanjut →
          </button>
        </div>
      </div>
    </DashboardLayout>
  );
}
