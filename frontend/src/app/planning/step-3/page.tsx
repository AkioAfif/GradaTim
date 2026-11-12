
"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ChevronDown, ChevronRight } from "lucide-react";

import DashboardLayout from "../../../components/DashboardLayout";

type Tab = "Overview" | "Task List" | "Schedule" | "Review";

type Sprint = {
  id: number;
  title: string;
  weeks: string;
  description: string;
  tasks: string[];
};

const exampleSprints: Sprint[] = [
  {
    id: 1,
    title: "Foundation",
    weeks: "Week 1–2",
    description: "Membangun pemahaman dasar dan menentukan target belajar.",
    tasks: [
      "Membaca materi dasar",
      "Membuat ringkasan konsep",
      "Mengerjakan latihan awal",
    ],
  },
  {
    id: 2,
    title: "Build Regular",
    weeks: "Week 3–4",
    description: "Membangun rutinitas dan meningkatkan konsistensi.",
    tasks: [
      "Mengerjakan latihan lanjutan",
      "Membuat jadwal belajar rutin",
      "Melakukan evaluasi mingguan",
    ],
  },
  {
    id: 3,
    title: "Advance",
    weeks: "Week 5–6",
    description: "Memperdalam materi dan menyelesaikan tugas yang lebih sulit.",
    tasks: [
      "Mempelajari materi lanjutan",
      "Mengerjakan studi kasus",
      "Melakukan review hasil latihan",
    ],
  },
  {
    id: 4,
    title: "Final Prep",
    weeks: "Week 7–8",
    description: "Menyelesaikan persiapan akhir dan evaluasi.",
    tasks: [
      "Mengulang materi penting",
      "Mengerjakan simulasi akhir",
      "Mengevaluasi pencapaian target",
    ],
  },
];

export default function PlanningStep3() {
  const router = useRouter();

  const [activeTab, setActiveTab] = useState<Tab>("Overview");
  const [expandedSprint, setExpandedSprint] = useState<number | null>(null);
  const [draftTitle, setDraftTitle] = useState("");
  const [hasDraft, setHasDraft] = useState(false);

  useEffect(() => {
    try {
      const saved = sessionStorage.getItem(
        "gradatim-planning-draft"
      );

      if (!saved) return;

      const draft = JSON.parse(saved);

      setDraftTitle(
        typeof draft.title === "string" ? draft.title : ""
      );
      setHasDraft(true);
    } catch (error) {
      console.error("Gagal membaca draft perencanaan:", error);
    }
  }, []);

  function handleConfirm() {
    try {
      const saved = sessionStorage.getItem(
        "gradatim-planning-draft"
      );

      if (!saved) {
        alert("Lengkapi Langkah 1 terlebih dahulu.");
        router.push("/planning/step-1");
        return;
      }

      const draft = JSON.parse(saved);

      sessionStorage.setItem(
        "gradatim-planning-draft",
        JSON.stringify({
          ...draft,
          sprintPreview: exampleSprints,
          sprintConfirmed: true,
        })
      );

      // Wizard masih berlanjut ke Langkah 4.
      // Sprint belum dikirim ke backend.
      router.push("/planning/step-4");
    } catch (error) {
      console.error("Gagal mengonfirmasi sprint:", error);
      alert("Gagal menyimpan rencana sementara.");
    }
  }

  return (
    <DashboardLayout>
      <div className="mx-auto max-w-5xl">
        {/* HEADER */}
        <header className="flex items-center justify-between border-b border-[#E9E0D4] pb-5">
          <p className="text-xs text-[#8B857B]">
            AI Planning / Sprint Breakdown
          </p>

          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-[#D7B99B] text-sm text-white">
            A
          </div>
        </header>

        {/* TITLE */}
        <section className="mt-7">
          <p className="text-xs font-bold tracking-[0.12em] text-[#506851]">
            LANGKAH 3 DARI 7
          </p>

          <h1 className="mt-3 text-3xl font-medium tracking-tight md:text-4xl">
            Rencana Sprint Belajarmu
          </h1>

          <p className="mt-3 text-sm text-[#8B857B]">
            Target besar menjadi langkah kecil yang realistis.
          </p>
        </section>

        {/* TABS */}
        <div className="mt-7 flex flex-wrap gap-3">
          {(["Overview", "Task List", "Schedule", "Review"] as Tab[]).map(
            (tab) => (
              <button
                key={tab}
                type="button"
                onClick={() => setActiveTab(tab)}
                className={`rounded-full px-5 py-2.5 text-sm transition ${
                  activeTab === tab
                    ? "bg-[#F0C4A4] text-[#45382E]"
                    : "bg-[#ECE9E1] text-[#57564F] hover:bg-[#E2DDD3]"
                }`}
              >
                {tab}
              </button>
            )
          )}
        </div>

        {/* CONTENT */}
        <section className="mt-3 rounded-xl border border-[#E7DBCC] bg-[#FFFCF7] p-5">
          {activeTab === "Overview" && (
            <div className="space-y-3">
              {exampleSprints.map((sprint) => {
                const expanded = expandedSprint === sprint.id;

                return (
                  <div
                    key={sprint.id}
                    className="overflow-hidden rounded-lg border border-[#E7DBCC] bg-[#F5EEE4]"
                  >
                    <button
                      type="button"
                      onClick={() =>
                        setExpandedSprint(
                          expanded ? null : sprint.id
                        )
                      }
                      className="flex w-full items-center justify-between gap-3 px-4 py-4 text-left text-sm font-semibold"
                    >
                      <span>
                        Sprint {sprint.id} — {sprint.title} (
                        {sprint.weeks})
                      </span>

                      {expanded ? (
                        <ChevronDown size={16} />
                      ) : (
                        <ChevronRight size={16} />
                      )}
                    </button>

                    {expanded && (
                      <div className="border-t border-[#E7DBCC] px-4 py-4">
                        <p className="text-sm text-[#8B857B]">
                          {sprint.description}
                        </p>

                        <ul className="mt-3 list-disc space-y-2 pl-5 text-sm">
                          {sprint.tasks.map((task) => (
                            <li key={task}>{task}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}

          {activeTab === "Task List" && (
            <div>
              <h2 className="text-lg font-semibold">
                Daftar Tugas Sprint
              </h2>

              <p className="mt-2 text-sm text-[#8B857B]">
                Contoh pembagian tugas untuk setiap sprint.
              </p>

              <div className="mt-5 space-y-5">
                {exampleSprints.map((sprint) => (
                  <div key={sprint.id}>
                    <h3 className="text-sm font-semibold text-[#506851]">
                      Sprint {sprint.id} — {sprint.title}
                    </h3>

                    <ul className="mt-2 list-disc space-y-2 pl-5 text-sm">
                      {sprint.tasks.map((task) => (
                        <li key={task}>{task}</li>
                      ))}
                    </ul>
                  </div>
                ))}
              </div>
            </div>
          )}

          {activeTab === "Schedule" && (
            <div>
              <h2 className="text-lg font-semibold">
                Jadwal Sprint
              </h2>

              <div className="mt-5 space-y-3">
                {exampleSprints.map((sprint) => (
                  <div
                    key={sprint.id}
                    className="flex flex-wrap items-center justify-between gap-2 rounded-lg bg-[#F5EEE4] px-4 py-4"
                  >
                    <span className="text-sm font-medium">
                      Sprint {sprint.id} — {sprint.title}
                    </span>

                    <span className="text-xs text-[#8B857B]">
                      {sprint.weeks}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {activeTab === "Review" && (
            <div>
              <h2 className="text-lg font-semibold">
                Review Rencana
              </h2>

              <div className="mt-5 rounded-lg bg-[#F5EEE4] p-5">
                <p className="text-xs text-[#8B857B]">
                  Target yang sedang direncanakan
                </p>

                <p className="mt-2 text-lg font-semibold">
                  {draftTitle || "Belum ada target"}
                </p>

                <p className="mt-3 text-sm text-[#8B857B]">
                  Rencana contoh terdiri dari 4 sprint
                  selama 8 minggu.
                </p>

                {!hasDraft && (
                  <p className="mt-3 text-sm text-[#A64C43]">
                    Draft belum ditemukan. Isi Langkah 1
                    sebelum mengonfirmasi rencana.
                  </p>
                )}
              </div>
            </div>
          )}
        </section>

        {/* NAVIGATION */}
        <div className="mt-5 flex flex-wrap items-center justify-between gap-4">
          <Link
            href="/planning/step-2"
            className="rounded-lg border border-[#DDD2C3] bg-[#ECE9E1] px-5 py-3 text-sm font-medium"
          >
            ← Kembali
          </Link>

          <button
            type="button"
            onClick={handleConfirm}
            className="rounded-lg bg-[#826049] px-6 py-3 text-sm font-medium text-white hover:bg-[#6D4D38]"
          >
            Konfirmasi Rencana
          </button>
        </div>

        <p className="mt-4 text-xs text-[#9A8F81]">
          Pratinjau sprint menggunakan data contoh.
          Integrasi AI Planning akan dilakukan setelah API siap.
        </p>
      </div>
    </DashboardLayout>
  );
}
