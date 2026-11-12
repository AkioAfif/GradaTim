
"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import DashboardLayout from "../../../components/DashboardLayout";
import type { Task } from "../../../context/TaskContext";

export default function PlanningStep1() {
  const router = useRouter();

  const [title, setTitle] = useState("");
  const [deadline, setDeadline] = useState("");
  const [category, setCategory] = useState("");
  const [priority, setPriority] = useState<Task["priority"]>("Medium");

  
function handleSubmit(event: FormEvent<HTMLFormElement>) {
  event.preventDefault();

  if (!title.trim() || !deadline || !category) return;

  sessionStorage.setItem(
    "gradatim-planning-draft",
    JSON.stringify({
      title: title.trim(),
      deadline,
      category,
      priority,
    })
  );

  router.push("/planning/step-2");
}


  return (
    <DashboardLayout>
      <div className="mx-auto max-w-5xl">
        <header className="flex items-center justify-between border-b border-[#E9E0D4] pb-5">
          <p className="text-xs text-[#8B857B]">
            Perencanaan / Detail Tugas
          </p>
          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-[#D7B99B] text-sm text-white">
            A
          </div>
        </header>

        <section className="mt-7">
          <p className="text-xs font-bold tracking-[0.12em] text-[#506851]">
            LANGKAH 1 DARI 7
          </p>

          <h1 className="mt-3 text-3xl font-medium md:text-4xl">
            Tambahkan Detail Tugas
          </h1>

          <p className="mt-3 text-sm text-[#8B857B]">
            Mulai dari hal sederhana untuk membangun rencana yang terarah.
          </p>
        </section>

        <form onSubmit={handleSubmit}>
          <div className="mt-7 rounded-xl border border-[#E7DBCC] bg-[#FFFCF7] p-5 sm:p-7">
            <div>
              <label htmlFor="title" className="mb-2 block text-sm font-semibold">
                Judul Tugas
              </label>
              <input
                id="title"
                required
                maxLength={150}
                value={title}
                onChange={(event) => setTitle(event.target.value)}
                placeholder="Contoh: Menyelesaikan materi machine learning"
                className="w-full rounded-lg border border-[#E5D9C9] bg-white px-4 py-3 text-sm outline-none focus:border-[#64765C]"
              />
            </div>

            <div className="mt-6 grid gap-4 sm:grid-cols-2">
              <div>
                <label htmlFor="deadline" className="mb-2 block text-sm font-semibold">
                  Target Deadline
                </label>
                <input
                  id="deadline"
                  type="date"
                  required
                  value={deadline}
                  onChange={(event) => setDeadline(event.target.value)}
                  className="w-full rounded-lg border border-[#E5D9C9] bg-white px-4 py-3 text-sm outline-none focus:border-[#64765C]"
                />
              </div>

              <div>
                <label htmlFor="category" className="mb-2 block text-sm font-semibold">
                  Kategori
                </label>
                <select
                  id="category"
                  required
                  value={category}
                  onChange={(event) => setCategory(event.target.value)}
                  className="w-full rounded-lg border border-[#E5D9C9] bg-white px-4 py-3 text-sm outline-none focus:border-[#64765C]"
                >
                  <option value="">Pilih kategori</option>
                  <option value="Kuliah">Kuliah</option>
                  <option value="Organisasi">Organisasi</option>
                  <option value="Proyek">Proyek</option>
                  <option value="Pribadi">Pribadi</option>
                  <option value="Lainnya">Lainnya</option>
                </select>
              </div>
            </div>

            <fieldset className="mt-6">
              <legend className="mb-3 text-sm font-semibold">
                Prioritas
              </legend>

              <div className="flex flex-wrap gap-3">
                {(["Low", "Medium", "High"] as const).map((value) => (
                  <label
                    key={value}
                    className={`cursor-pointer rounded-full px-5 py-2 text-sm ${
                      priority === value
                        ? "bg-[#F0C4A4] text-[#45382E]"
                        : "bg-[#ECE9E1] text-[#57564F]"
                    }`}
                  >
                    <input
                      type="radio"
                      name="priority"
                      value={value}
                      checked={priority === value}
                      onChange={() => setPriority(value)}
                      className="mr-2 accent-[#826049]"
                    />
                    {value}
                  </label>
                ))}
              </div>
            </fieldset>
          </div>

          <div className="mt-5 flex items-center justify-between gap-4">
            <Link
              href="/"
              className="rounded-lg border border-[#DDD2C3] bg-[#ECE9E1] px-5 py-3 text-sm font-medium"
            >
              ← Kembali
            </Link>

            <button
              type="submit"
              className="rounded-lg bg-[#826049] px-6 py-3 text-sm font-medium text-white hover:bg-[#6D4D38]"
            >
              Simpan &amp; Lanjut →
            </button>
          </div>
        </form>
      </div>
    </DashboardLayout>
  );
}
