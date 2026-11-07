
"use client";

import { useMemo, useState } from "react";
import {
  CalendarDays,
  CheckCircle2,
  Circle,
  Pencil,
  Plus,
  Search,
  Trash2,
  X,
} from "lucide-react";

import DashboardLayout from "../../components/DashboardLayout";
import { useTasks, type Task } from "../../context/TaskContext";

type Priority = Task["priority"];
type Filter = "all" | "active" | "completed";

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

const priorityStyles: Record<Priority, string> = {
  Low: "bg-[#E8EFE5] text-[#55724E]",
  Medium: "bg-[#F5E7D2] text-[#946B3D]",
  High: "bg-[#F5DDDA] text-[#A64C43]",
};

function formatDeadline(value: string) {
  if (!value) return "Tanpa deadline";

  const date = new Date(`${value}T00:00:00`);

  if (Number.isNaN(date.getTime())) return value;

  return date.toLocaleDateString("id-ID", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}

export default function TasksPage() {
  const {
    tasks,
    addTask,
    updateTask,
    deleteTask,
    toggleTask,
  } = useTasks();

  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState<Filter>("all");
  const [form, setForm] = useState<TaskForm>(emptyForm);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [isFormOpen, setIsFormOpen] = useState(false);

  const completedCount = tasks.filter(
    (task) => task.completed
  ).length;

  const activeCount = tasks.length - completedCount;

  const filteredTasks = useMemo(() => {
    return tasks
      .filter((task) =>
        task.title.toLowerCase().includes(
          search.trim().toLowerCase()
        )
      )
      .filter((task) => {
        if (filter === "active") return !task.completed;
        if (filter === "completed") return task.completed;
        return true;
      })
      .sort((a, b) => {
        if (a.completed !== b.completed) {
          return Number(a.completed) - Number(b.completed);
        }

        if (!a.deadline) return 1;
        if (!b.deadline) return -1;

        return a.deadline.localeCompare(b.deadline);
      });
  }, [tasks, search, filter]);

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
      <div className="mx-auto max-w-6xl">
        {/* HEADER */}
        <header className="flex flex-wrap items-center justify-between gap-5">
          <div>
            <p className="text-sm text-[#8A7A69]">
              Personal Productivity Planner
            </p>

            <h1 className="mt-2 font-serif text-4xl font-semibold">
              Manajemen Tugas
            </h1>

            <p className="mt-3 text-sm text-[#817769]">
              Atur prioritas, pantau deadline, dan selesaikan
              tugasmu satu per satu.
            </p>
          </div>

          <button
            type="button"
            onClick={openAddForm}
            className="flex items-center gap-2 rounded-xl bg-[#826049] px-5 py-3 text-sm font-semibold text-white transition hover:bg-[#6D4D38]"
          >
            <Plus size={18} />
            Tambah Tugas
          </button>
        </header>

        {/* STATISTICS */}
        <section className="mt-9 grid gap-4 sm:grid-cols-3">
          <StatCard
            label="Total Tugas"
            value={tasks.length}
            icon={<CalendarDays size={23} />}
          />

          <StatCard
            label="Belum Selesai"
            value={activeCount}
            icon={<Circle size={23} />}
          />

          <StatCard
            label="Selesai"
            value={completedCount}
            icon={<CheckCircle2 size={23} />}
          />
        </section>

        {/* TASK LIST */}
        <section className="mt-8 rounded-2xl border border-[#E9DED0] bg-white p-5 shadow-sm sm:p-7">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <h2 className="font-serif text-2xl font-semibold">
              Daftar Tugas
            </h2>

            <div className="flex items-center gap-2 rounded-xl border border-[#E8DED1] bg-[#FAF6EE] px-4 py-2.5">
              <Search size={18} className="text-[#8A7A69]" />

              <input
                type="search"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Cari tugas..."
                aria-label="Cari tugas"
                className="w-44 bg-transparent text-sm outline-none sm:w-56"
              />
            </div>
          </div>

          {/* FILTER */}
          <div className="mt-6 flex flex-wrap gap-2">
            {(
              [
                { value: "all", label: "Semua" },
                { value: "active", label: "Belum Selesai" },
                { value: "completed", label: "Selesai" },
              ] as const
            ).map((item) => (
              <button
                key={item.value}
                type="button"
                onClick={() => setFilter(item.value)}
                aria-pressed={filter === item.value}
                className={`rounded-full px-4 py-2 text-sm font-medium transition ${
                  filter === item.value
                    ? "bg-[#64765C] text-white"
                    : "bg-[#F2EEE6] text-[#625D53] hover:bg-[#E7E1D5]"
                }`}
              >
                {item.label}
              </button>
            ))}
          </div>

          {/* TASK ITEMS */}
          <div className="mt-6 space-y-3">
            {filteredTasks.length === 0 ? (
              <div className="rounded-xl border border-dashed border-[#DDD2C3] bg-[#FAF6EE] px-5 py-12 text-center">
                <p className="font-medium text-[#625D53]">
                  Belum ada tugas yang cocok.
                </p>
                <p className="mt-2 text-sm text-[#8A7A69]">
                  Coba ubah pencarian atau tambahkan tugas baru.
                </p>
              </div>
            ) : (
              filteredTasks.map((task) => (
                <article
                  key={task.id}
                  className="flex flex-wrap items-center gap-4 rounded-xl border border-[#E9DED0] bg-[#FFF9F0] p-4 transition hover:border-[#C7B7A5]"
                >
                  <input
                    type="checkbox"
                    checked={task.completed}
                    onChange={() => toggleTask(task.id)}
                    aria-label={`Tandai ${task.title} ${
                      task.completed
                        ? "belum selesai"
                        : "selesai"
                    }`}
                    className="h-5 w-5 shrink-0 accent-[#64765C]"
                  />

                  <div className="min-w-0 flex-1">
                    <h3
                      className={`break-words font-medium ${
                        task.completed
                          ? "text-[#A49A8C] line-through"
                          : "text-[#30312B]"
                      }`}
                    >
                      {task.title}
                    </h3>

                    <div className="mt-2 flex flex-wrap items-center gap-3">
                      <span
                        className={`rounded-full px-3 py-1 text-xs font-medium ${
                          priorityStyles[task.priority] ??
                          priorityStyles.Medium
                        }`}
                      >
                        {priorityLabels[task.priority] ??
                          "Sedang"}
                      </span>

                      <span className="flex items-center gap-1.5 text-xs text-[#817769]">
                        <CalendarDays size={14} />
                        {formatDeadline(task.deadline)}
                      </span>
                    </div>
                  </div>

                  <div className="ml-auto flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => openEditForm(task)}
                      aria-label={`Edit ${task.title}`}
                      title="Edit tugas"
                      className="rounded-lg border border-[#E5D9C9] bg-white p-2.5 text-[#64765C] hover:bg-[#EEF1EB]"
                    >
                      <Pencil size={17} />
                    </button>

                    <button
                      type="button"
                      onClick={() => handleDelete(task)}
                      aria-label={`Hapus ${task.title}`}
                      title="Hapus tugas"
                      className="rounded-lg border border-[#E5D9C9] bg-white p-2.5 text-[#A64C43] hover:bg-[#F9E9E6]"
                    >
                      <Trash2 size={17} />
                    </button>
                  </div>
                </article>
              ))
            )}
          </div>

          <p className="mt-5 text-xs text-[#9A8F81]">
            Menampilkan {filteredTasks.length} dari {tasks.length} tugas.
          </p>
        </section>
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
            <div className="flex items-center justify-between gap-4">
              <h2
                id="task-form-title"
                className="font-serif text-2xl font-semibold"
              >
                {editingId ? "Edit Tugas" : "Tambah Tugas"}
              </h2>

              <button
                type="button"
                onClick={closeForm}
                aria-label="Tutup formulir"
                className="rounded-lg p-2 text-[#817769] hover:bg-[#F2EEE6]"
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
                  placeholder="Contoh: Belajar materi statistika"
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
                  className="rounded-xl border border-[#DDD2C3] px-5 py-3 text-sm font-medium text-[#625D53] hover:bg-[#F2EEE6]"
                >
                  Batal
                </button>

                <button
                  type="submit"
                  className="rounded-xl bg-[#826049] px-6 py-3 text-sm font-semibold text-white hover:bg-[#6D4D38]"
                >
                  {editingId ? "Simpan Perubahan" : "Simpan Tugas"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </DashboardLayout>
  );
}

function StatCard({
  label,
  value,
  icon,
}: {
  label: string;
  value: number;
  icon: React.ReactNode;
}) {
  return (
    <div className="flex items-center justify-between rounded-2xl border border-[#E9DED0] bg-white p-6 shadow-sm">
      <div>
        <p className="text-sm text-[#817769]">{label}</p>
        <p className="mt-2 text-3xl font-bold text-[#30312B]">
          {value}
        </p>
      </div>

      <div className="rounded-xl bg-[#E8EFE5] p-3 text-[#64765C]">
        {icon}
      </div>
    </div>
  );
}
