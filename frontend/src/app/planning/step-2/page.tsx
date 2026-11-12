
"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import DashboardLayout from "../../../components/DashboardLayout";

type PreferenceGroup = {
  title: string;
  key: "commitments" | "constraints" | "preferences";
  options: string[];
};

const groups: PreferenceGroup[] = [
  {
    title: "Recurring Commitments",
    key: "commitments",
    options: ["Kuliah", "Organisasi", "Kerja", "Lainnya"],
  },
  {
    title: "Deadline Constraints",
    key: "constraints",
    options: ["Tugas kuliah", "Proyek", "Ujian", "Lainnya"],
  },
  {
    title: "Preferences",
    key: "preferences",
    options: ["Waktu belajar", "Durasi fokus", "Metode belajar", "Lainnya"],
  },
];

type Selections = {
  commitments: string[];
  constraints: string[];
  preferences: string[];
};

const emptySelections: Selections = {
  commitments: [],
  constraints: [],
  preferences: [],
};

export default function PlanningStep2() {
  const router = useRouter();
  const [selections, setSelections] =
    useState<Selections>(emptySelections);

  useEffect(() => {
    try {
      const saved = sessionStorage.getItem(
        "gradatim-planning-draft"
      );

      if (!saved) return;

      const draft = JSON.parse(saved);

      if (draft.selections) {
        setSelections({
          ...emptySelections,
          ...draft.selections,
        });
      }
    } catch (error) {
      console.error("Gagal membaca draft:", error);
    }
  }, []);

  function toggleOption(
    key: PreferenceGroup["key"],
    option: string
  ) {
    setSelections((previous) => {
      const current = previous[key];

      return {
        ...previous,
        [key]: current.includes(option)
          ? current.filter((item) => item !== option)
          : [...current, option],
      };
    });
  }

  function handleNext() {
    try {
      const saved = sessionStorage.getItem(
        "gradatim-planning-draft"
      );

      if (!saved) {
        alert("Isi detail tugas pada Langkah 1 terlebih dahulu.");
        router.push("/planning/step-1");
        return;
      }

      const draft = JSON.parse(saved);

      sessionStorage.setItem(
        "gradatim-planning-draft",
        JSON.stringify({
          ...draft,
          selections,
        })
      );

      // Langkah 3 akan dibuat pada tahap berikutnya.
      router.push("/planning/step-3");
    } catch (error) {
      console.error("Gagal menyimpan preferensi:", error);
      alert("Terjadi kesalahan saat menyimpan preferensi.");
    }
  }

  return (
    <DashboardLayout>
      <div className="mx-auto max-w-5xl">
        <header className="flex items-center justify-between border-b border-[#E9E0D4] pb-5">
          <p className="text-xs text-[#8B857B]">
            Perencanaan / Preferensi
          </p>

          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-[#D7B99B] text-sm text-white">
            A
          </div>
        </header>

        <section className="mt-7">
          <p className="text-xs font-bold tracking-[0.12em] text-[#506851]">
            LANGKAH 2 DARI 7
          </p>

          <h1 className="mt-3 text-3xl font-medium tracking-tight md:text-4xl">
            Komitmen &amp; Preferensi
          </h1>

          <p className="mt-3 text-sm text-[#8B857B]">
            Sesuaikan rencana dengan rutinitas dan kebutuhanmu.
          </p>
        </section>

        <section className="mt-7 grid gap-4 lg:grid-cols-3">
          {groups.map((group) => (
            <div
              key={group.key}
              className="rounded-xl border border-[#E7DBCC] bg-[#F7EEE3] p-5"
            >
              <h2 className="text-base font-semibold">
                {group.title}
              </h2>

              <div className="mt-5 divide-y divide-[#EBE2D6]">
                {group.options.map((option) => (
                  <label
                    key={option}
                    className="flex cursor-pointer items-center gap-3 py-3 text-sm"
                  >
                    <input
                      type="checkbox"
                      checked={selections[group.key].includes(
                        option
                      )}
                      onChange={() =>
                        toggleOption(group.key, option)
                      }
                      className="h-4 w-4 accent-[#82947B]"
                    />

                    <span>{option}</span>
                  </label>
                ))}
              </div>
            </div>
          ))}
        </section>

        <div className="mt-10 flex items-center justify-between gap-4">
          <Link
            href="/planning/step-1"
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
