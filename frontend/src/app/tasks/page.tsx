
"use client";

import { useState } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  ArrowRight,
  Pencil,
  Plus,
  Trash2,
  X,
} from "lucide-react";

import DashboardLayout from "../../components/DashboardLayout";
import { useTasks, type Task } from "../../context/TaskContext";

type Priority = Task["priority"];
type Tab = "Tasks" | "Goals" | "Notes";

type TaskForm = {
  title: string;
  priority: Priority;
  deadline: string;
};

const emptyForm: TaskForm = {
  title: "",
  priority: "Medium",
  deadline: "",
};

const priorityLabels: Record<Priority, string> = {
  Low: "Rendah",
  Medium: "Sedang",
  High: "Tinggi",
};

export default function TasksPage() {
  const {
    tasks,
    addTask,
    updateTask,
    deleteTask,
    toggleTask,
  } = useTasks();

  const [activeTab, setActiveTab] = useState<Tab>("Tasks");
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState<TaskForm>(emptyForm);

  function openAddForm() {
    setEditingId(null);
    setForm(emptyForm);
    setIsFormOpen(true);
  }

  function openEditForm(task: Task) {
    setEditingId(task.id);
    setForm({
      title: task.title,
      priority: task.priority,
      deadline: task.deadline,
    });
    setIsFormOpen(true);
  }

  function closeForm() {
    setIsFormOpen(false);
    setEditingId(null);
    setForm(emptyForm);
  }

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const title = form.title.trim();
    if (!title) return;

    if (editingId !== null) {
      updateTask(editingId, {
        title,
        priority: form.priority,
        deadline: form.deadline,
      });
    } else {
      addTask({
        title,
        priority: form.priority,
        deadline: form.deadline,
        completed: false,
      });
    }

    closeForm();
  }

  function handleDelete(task: Task) {
    const confirmed = window.confirm(
      `Yakin ingin menghapus tugas "${task.title}"?`
    );

    if (confirmed) {
      deleteTask(task.id);
    }
  }

  return (
    <DashboardLayout>
      <div className="mx-auto max-w-5xl">
        {/* TOP BAR */}
        <header className="flex items-center justify-between border-b border-[#E9E0D4] pb-5">
          <p className="text-xs text-[#8B857B]">
            Task Management
          </p>

          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-[#D7B99B] text-sm font-medium text-white">
            A
          </div>
        </header>

        {/* PAGE HEADING */}
        <section className="mt-7">
          <p className="text-xs font-bold tracking-[0.12em] text-[#506851]">
            LANGKAH 6 DARI 7
          </p>

          <h1 className="mt-3 text-3xl font-medium tracking-tight md:text-4xl">
            Kelola Tugas &amp; Target
          </h1>

          <p className="mt-3 text-sm text-[#8B857B]">
            Prioritaskan aktivitas yang mendukung tujuanmu.
          </p>
        </section>

        {/* TABS AND ADD BUTTON */}
        <section className="mt-7 flex flex-wrap items-center justify-between gap-4">
          <div className="flex gap-3">
            {(["Tasks", "Goals", "Notes"] as Tab[]).map(
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

          <button
            type="button"
            onClick={openAddForm}
            className="flex items-center gap-2 rounded-lg bg-[#826049] px-5 py-3 text-sm font-medium text-white hover:bg-[#6D4D38]"
          >
            <Plus size={16} />
            Tambah Tugas
          </button>
        </section>

        {/* CONTENT */}
        {activeTab === "Tasks" ? (
          <section className="mt-3 overflow-hidden rounded-xl border border-[#E5D9C9] bg-white">
            <div className="overflow-x-auto">
              <table className="w-full min-w-[680px] border-collapse text-left text-sm">
                <thead className="bg-[#F1EADF]">
                  <tr>
                    <th className="px-4 py-4 font-semibold">
                      Task
                    </th>
                    <th className="px-4 py-4 font-semibold">
                      Est. Time
                    </th>
                    <th className="px-4 py-4 font-semibold">
                      Difficulty
                    </th>
                    <th className="px-4 py-4 font-semibold">
                      Energy
                    </th>
                    <th className="px-4 py-4 font-semibold">
                      Status
                    </th>
                    <th className="px-4 py-4 text-right font-semibold">
                      Aksi
                    </th>
                  </tr>
                </thead>

                <tbody className="divide-y divide-[#EEE6DA]">
                  {tasks.length === 0 ? (
                    <tr>
                      <td
                        colSpan={6}
                        className="px-4 py-12 text-center text-[#8B857B]"
                      >
                        Belum ada tugas. Klik Tambah Tugas
                        untuk membuat tugas pertamamu.
                      </td>
                    </tr>
                  ) : (
                    tasks.map((task) => (
                      <tr
                        key={task.id}
                        className="hover:bg-[#FFFAF3]"
                      >
                        <td className="px-4 py-4">
                          <div className="font-medium">
                            {task.title}
                          </div>

                          <div className="mt-1 text-xs text-[#8B857B]">
                            Prioritas:{" "}
                            {priorityLabels[task.priority] ??
                              "Sedang"}
                          </div>
                        </td>

                        <td className="px-4 py-4 text-[#8B857B]">
                          —
                        </td>

                        <td className="px-4 py-4 text-[#8B857B]">
                          —
                        </td>

                        <td className="px-4 py-4 text-[#8B857B]">
                          —
                        </td>

                        <td className="px-4 py-4">
                          <button
                            type="button"
                            onClick={() => toggleTask(task.id)}
                            title="Klik untuk mengubah status"
                            className={`rounded-md px-3 py-1.5 text-xs font-medium ${
                              task.completed
                                ? "bg-[#E2EBDD] text-[#506851]"
                                : "bg-[#F0E9DF] text-[#826049]"
                            }`}
                          >
                            {task.completed ? "Done" : "To Do"}
                          </button>
                        </td>

                        <td className="px-4 py-4">
                          <div className="flex justify-end gap-2">
                            <button
                              type="button"
                              onClick={() => openEditForm(task)}
                              title="Edit tugas"
                              aria-label={`Edit ${task.title}`}
                              className="rounded-lg p-2 text-[#64765C] hover:bg-[#EEF1EB]"
                            >
                              <Pencil size={17} />
                            </button>

                            <button
                              type="button"
                              onClick={() => handleDelete(task)}
                              title="Hapus tugas"
                              aria-label={`Hapus ${task.title}`}
                              className="rounded-lg p-2 text-[#A64C43] hover:bg-[#F9E9E6]"
                            >
                              <Trash2 size={17} />
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </section>
        ) : (
          <section className="mt-4 rounded-xl border border-[#E5D9C9] bg-[#F7EEE3] p-8 text-center">
            <h2 className="text-lg font-semibold">
              {activeTab}
            </h2>

            <p className="mt-3 text-sm text-[#8B857B]">
              Fitur {activeTab} akan diimplementasikan
              pada tahap berikutnya.
            </p>
          </section>
        )}

        
{/* NAVIGATION */}
<div className="mt-6 flex items-center justify-between gap-4">
  <Link
    href="/planning/step-5"
    className="flex items-center gap-2 rounded-lg border border-[#DDD2C3] bg-[#ECE9E1] px-5 py-3 text-sm font-medium hover:bg-[#E2DDD3]"
  >
    <ArrowLeft size={16} />
    Kembali
  </Link>

  <Link
    href="/planning/step-7"
    className="flex items-center gap-2 rounded-lg bg-[#826049] px-5 py-3 text-sm font-medium text-white hover:bg-[#6D4D38]"
  >
    Lanjut
    <ArrowRight size={16} />
  </Link>
</div>


      {/* ADD / EDIT MODAL */}
      {isFormOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="task-form-title"
            className="w-full max-w-lg rounded-2xl bg-[#FFFCF7] p-6 shadow-xl sm:p-8"
          >
            <div className="flex items-center justify-between">
              <h2
                id="task-form-title"
                className="text-2xl font-semibold"
              >
                {editingId ? "Edit Tugas" : "Tambah Tugas"}
              </h2>

              <button
                type="button"
                onClick={closeForm}
                aria-label="Tutup formulir"
                className="rounded-lg p-2 hover:bg-[#F2EEE6]"
              >
                <X size={20} />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="mt-7 space-y-5">
              <div>
                <label
                  htmlFor="task-title"
                  className="mb-2 block text-sm font-medium"
                >
                  Nama Tugas
                </label>

                <input
                  id="task-title"
                  required
                  maxLength={150}
                  value={form.title}
                  onChange={(event) =>
                    setForm({
                      ...form,
                      title: event.target.value,
                    })
                  }
                  placeholder="Masukkan nama tugas"
                  className="w-full rounded-xl border border-[#E5D9C9] bg-white px-4 py-3 text-sm outline-none focus:border-[#64765C]"
                />
              </div>

              <div>
                <label
                  htmlFor="task-priority"
                  className="mb-2 block text-sm font-medium"
                >
                  Prioritas
                </label>

                <select
                  id="task-priority"
                  value={form.priority}
                  onChange={(event) =>
                    setForm({
                      ...form,
                      priority: event.target.value as Priority,
                    })
                  }
                  className="w-full rounded-xl border border-[#E5D9C9] bg-white px-4 py-3 text-sm outline-none focus:border-[#64765C]"
                >
                  <option value="Low">Rendah</option>
                  <option value="Medium">Sedang</option>
                  <option value="High">Tinggi</option>
                </select>
              </div>

              <div>
                <label
                  htmlFor="task-deadline"
                  className="mb-2 block text-sm font-medium"
                >
                  Deadline
                </label>

                <input
                  id="task-deadline"
                  type="date"
                  value={form.deadline}
                  onChange={(event) =>
                    setForm({
                      ...form,
                      deadline: event.target.value,
                    })
                  }
                  className="w-full rounded-xl border border-[#E5D9C9] bg-white px-4 py-3 text-sm outline-none focus:border-[#64765C]"
                />
              </div>

              <div className="flex justify-end gap-3 pt-3">
                <button
                  type="button"
                  onClick={closeForm}
                  className="rounded-lg border border-[#DDD2C3] px-5 py-3 text-sm"
                >
                  Batal
                </button>

                <button
                  type="submit"
                  className="rounded-lg bg-[#826049] px-5 py-3 text-sm font-medium text-white"
                >
                  {editingId
                    ? "Simpan Perubahan"
                    : "Simpan Tugas"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
      </div>
    </DashboardLayout>
  );
}
