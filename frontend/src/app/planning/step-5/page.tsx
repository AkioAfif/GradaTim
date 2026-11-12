
"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import DashboardLayout from "../../../components/DashboardLayout";

type EnergyLevel = "Low" | "Medium" | "High";

export default function PlanningStep5() {
  const router = useRouter();

  const [sprintDuration, setSprintDuration] = useState("2");
  const [blockedStart, setBlockedStart] = useState("");
  const [blockedEnd, setBlockedEnd] = useState("");
  const [energyLevel, setEnergyLevel] =
    useState<EnergyLevel>("Medium");
  const [error, setError] = useState("");

  // Membaca data yang pernah disimpan saat kembali ke halaman ini.
  useEffect(() => {
    try {
      const saved = sessionStorage.getItem(
        "gradatim-planning-draft"
      );

      if (!saved) return;

      const draft = JSON.parse(saved);

      if (typeof draft.sprintDuration === "string") {
        setSprintDuration(draft.sprintDuration);
      }

      if (typeof draft.blockedStart === "string") {
        setBlockedStart(draft.blockedStart);
      }

      if (typeof draft.blockedEnd === "string") {
        setBlockedEnd(draft.blockedEnd);
      }

      if (
        draft.energyLevel === "Low" ||
        draft.energyLevel === "Medium" ||
        draft.energyLevel === "High"
      ) {
        setEnergyLevel(draft.energyLevel);
      }
    } catch (error) {
      console.error("Gagal membaca draft:", error);
    }
  }, []);

  function handleNext() {
    setError("");

    if (blockedStart && !blockedEnd) {
      setError("Isi tanggal selesai untuk Blocked Periods.");
      return;
    }

    if (!blockedStart && blockedEnd) {
      setError("Isi tanggal mulai untuk Blocked Periods.");
      return;
    }

    if (
      blockedStart &&
      blockedEnd &&
      blockedEnd < blockedStart
    ) {
      setError(
        "Tanggal selesai tidak boleh lebih awal dari tanggal mulai."
      );
      return;
    }

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
          sprintDuration,
          blockedStart,
          blockedEnd,
          energyLevel,
        })
      );

      router.push("/tasks");
    } catch (error) {
      console.error("Gagal menyimpan parameter:", error);
      setError("Terjadi kesalahan saat menyimpan parameter.");
    }
  }

  return (
    <DashboardLayout>
      <div className="mx-auto max-w-5xl">
        {/* HEADER */}
        <header className="flex items-center justify-between border-b border-[#E9E0D4] pb-5">
          <p className="text-xs text-[#8B857B]">
            Planning Parameters
          </p>

          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-[#D7B99B] text-sm text-white">
            A
          </div>
        </header>

        {/* PAGE TITLE */}
        <section className="mt-7">
          <p className="text-xs font-bold tracking-[0.12em] text-[#506851]">
            LANGKAH 5 DARI 7
          </p>

          <h1 className="mt-3 text-3xl font-medium tracking-tight md:text-4xl">
            Atur Parameter Rencana
          </h1>

          <p className="mt-3 text-sm text-[#8B857B]">
            Sesuaikan durasi, waktu yang tersedia, dan energimu.
          </p>
        </section>

        {/* PARAMETER FORM */}
        <section className="mt-7 rounded-xl border border-[#E7DBCC] bg-[#FFFCF7] p-5 sm:p-7">
          {/* SPRINT DURATION */}
          <div>
            <label
              htmlFor="sprint-duration"
              className="mb-2 block text-sm font-semibold"
            >
              Sprint Duration
            </label>

            <select
              id="sprint-duration"
              value={sprintDuration}
              onChange={(event) =>
                setSprintDuration(event.target.value)
              }
              className="w-full rounded-lg border border-[#E5D9C9] bg-white px-4 py-3 text-sm outline-none focus:border-[#64765C]"
            >
              <option value="1">1 week</option>
              <option value="2">2 weeks</option>
              <option value="3">3 weeks</option>
              <option value="4">4 weeks</option>
            </select>
          </div>

          {/* BLOCKED PERIODS */}
          <div className="mt-6">
            <p className="mb-2 text-sm font-semibold">
              Blocked Periods
            </p>

            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label
                  htmlFor="blocked-start"
                  className="mb-2 block text-xs text-[#8B857B]"
                >
                  Mulai
                </label>

                <input
                  id="blocked-start"
                  type="date"
                  value={blockedStart}
                  onChange={(event) =>
                    setBlockedStart(event.target.value)
                  }
                  className="w-full rounded-lg border border-[#E5D9C9] bg-white px-4 py-3 text-sm outline-none focus:border-[#64765C]"
                />
              </div>

              <div>
                <label
                  htmlFor="blocked-end"
                  className="mb-2 block text-xs text-[#8B857B]"
                >
                  Selesai
                </label>

                <input
                  id="blocked-end"
                  type="date"
                  min={blockedStart || undefined}
                  value={blockedEnd}
                  onChange={(event) =>
                    setBlockedEnd(event.target.value)
                  }
                  className="w-full rounded-lg border border-[#E5D9C9] bg-white px-4 py-3 text-sm outline-none focus:border-[#64765C]"
                />
              </div>
            </div>

            <p className="mt-2 text-xs text-[#8B857B]">
              Opsional. Isi jika ada periode ketika kamu
              tidak bisa menjalankan rencana.
            </p>
          </div>

          {/* ENERGY LEVEL */}
          <fieldset className="mt-7">
            <legend className="mb-3 text-sm font-semibold">
              Energy Level
            </legend>

            <div className="flex flex-wrap gap-3">
              {(["Low", "Medium", "High"] as const).map(
                (level) => (
                  <label
                    key={level}
                    className={`cursor-pointer rounded-full px-5 py-2 text-sm transition ${
                      energyLevel === level
                        ? "bg-[#F0C4A4] text-[#45382E]"
                        : "bg-[#ECE9E1] text-[#57564F] hover:bg-[#E2DDD3]"
                    }`}
                  >
                    <input
                      type="radio"
                      name="energy-level"
                      value={level}
                      checked={energyLevel === level}
                      onChange={() => setEnergyLevel(level)}
                      className="mr-2 accent-[#826049]"
                    />

                    {level}
                  </label>
                )
              )}
            </div>
          </fieldset>
        </section>

        {/* ERROR MESSAGE */}
        {error && (
          <p
            role="alert"
            className="mt-4 text-sm text-red-700"
          >
            {error}
          </p>
        )}

        {/* NAVIGATION */}
        <div className="mt-5 flex items-center justify-between gap-4">
          <Link
            href="/planning/step-4"
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
