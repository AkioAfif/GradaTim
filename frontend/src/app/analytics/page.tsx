
"use client";

import { useMemo } from "react";
import {
  Activity,
  AlertTriangle,
  CalendarClock,
  CheckCircle2,
  Circle,
  ListTodo,
  Target,
  TrendingUp,
} from "lucide-react";

import DashboardLayout from "../../components/DashboardLayout";
import { useTasks } from "../../context/TaskContext";

const priorityColors = {
  High: "#C98076",
  Medium: "#C9A36D",
  Low: "#8D9B80",
};

const priorityLabels = {
  High: "Tinggi",
  Medium: "Sedang",
  Low: "Rendah",
};

function getLocalDateKey(date: Date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");

  return `${year}-${month}-${day}`;
}

function formatDeadline(value: string) {
  if (!value) return "Tanpa deadline";

  const date = new Date(`${value}T00:00:00`);

  if (Number.isNaN(date.getTime())) return value;

  return date.toLocaleDateString("id-ID", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

export default function AnalyticsPage() {
  const { tasks } = useTasks();

  const stats = useMemo(() => {
    const total = tasks.length;
    const completed = tasks.filter(
      (task) => task.completed
    ).length;

    const active = total - completed;

    const completionRate = total
      ? Math.round((completed / total) * 100)
      : 0;

    const priorityCounts = {
      High: tasks.filter(
        (task) => task.priority === "High"
      ).length,
      Medium: tasks.filter(
        (task) => task.priority === "Medium"
      ).length,
      Low: tasks.filter(
        (task) => task.priority === "Low"
      ).length,
    };

    const today = new Date();
    today.setHours(0, 0, 0, 0);

    const todayKey = getLocalDateKey(today);

    const sevenDaysLater = new Date(today);
    sevenDaysLater.setDate(
      sevenDaysLater.getDate() + 7
    );

    const sevenDaysKey = getLocalDateKey(
      sevenDaysLater
    );

    const overdue = tasks.filter(
      (task) =>
        !task.completed &&
        task.deadline &&
        task.deadline < todayKey
    ).length;

    const upcoming = tasks.filter(
      (task) =>
        !task.completed &&
        task.deadline &&
        task.deadline >= todayKey &&
        task.deadline <= sevenDaysKey
    ).length;

    const highPriorityTasks = tasks
      .filter(
        (task) =>
          !task.completed &&
          task.priority === "High"
      )
      .sort((a, b) => {
        if (!a.deadline) return 1;
        if (!b.deadline) return -1;

        return a.deadline.localeCompare(
          b.deadline
        );
      })
      .slice(0, 5);

    return {
      total,
      completed,
      active,
      completionRate,
      priorityCounts,
      overdue,
      upcoming,
      highPriorityTasks,
    };
  }, [tasks]);

  const priorityData = [
    {
      label: "Tinggi",
      value: stats.priorityCounts.High,
      color: priorityColors.High,
    },
    {
      label: "Sedang",
      value: stats.priorityCounts.Medium,
      color: priorityColors.Medium,
    },
    {
      label: "Rendah",
      value: stats.priorityCounts.Low,
      color: priorityColors.Low,
    },
  ];

  return (
    <DashboardLayout>
      <div className="mx-auto max-w-6xl">
        {/* HEADER */}
        <header>
          <p className="text-sm text-[#8A7A69]">
            Personal Productivity Planner
          </p>

          <h1 className="mt-2 font-serif text-4xl font-semibold">
            Analitik
          </h1>

          <p className="mt-3 text-sm text-[#817769]">
            Pantau perkembangan tugas dan kenali
            prioritas yang perlu kamu selesaikan.
          </p>
        </header>

        {/* SUMMARY CARDS */}
        <section className="mt-9 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <StatCard
            label="Total Tugas"
            value={stats.total}
            icon={<ListTodo size={22} />}
          />

          <StatCard
            label="Selesai"
            value={stats.completed}
            icon={<CheckCircle2 size={22} />}
          />

          <StatCard
            label="Belum Selesai"
            value={stats.active}
            icon={<Circle size={22} />}
          />

          <StatCard
            label="Completion Rate"
            value={`${stats.completionRate}%`}
            icon={<TrendingUp size={22} />}
          />
        </section>

        {/* CHARTS */}
        <section className="mt-8 grid gap-6 xl:grid-cols-2">
          {/* COMPLETION CHART */}
          <div className="rounded-2xl border border-[#E9DED0] bg-white p-7 shadow-sm">
            <div className="flex items-center gap-3">
              <Target
                size={23}
                className="text-[#64765C]"
              />

              <h2 className="font-serif text-xl font-semibold">
                Penyelesaian Tugas
              </h2>
            </div>

            <p className="mt-2 text-sm text-[#817769]">
              Perbandingan tugas selesai dan belum selesai.
            </p>

            <div className="mt-9 flex flex-col items-center">
              <div
                role="img"
                aria-label={`${stats.completionRate}% tugas selesai`}
                className="relative flex h-48 w-48 items-center justify-center rounded-full"
                style={{
                  background: `conic-gradient(
                    #8D9B80 0% ${stats.completionRate}%,
                    #EEE8DE ${stats.completionRate}% 100%
                  )`,
                }}
              >
                <div className="flex h-36 w-36 flex-col items-center justify-center rounded-full bg-white">
                  <span className="text-4xl font-bold text-[#64765C]">
                    {stats.completionRate}%
                  </span>

                  <span className="mt-1 text-xs text-[#817769]">
                    Selesai
                  </span>
                </div>
              </div>

              <div className="mt-8 flex flex-wrap justify-center gap-5 text-sm">
                <Legend
                  color="#8D9B80"
                  label={`Selesai (${stats.completed})`}
                />

                <Legend
                  color="#EEE8DE"
                  label={`Belum selesai (${stats.active})`}
                />
              </div>
            </div>
          </div>

          {/* PRIORITY CHART */}
          <div className="rounded-2xl border border-[#E9DED0] bg-white p-7 shadow-sm">
            <div className="flex items-center gap-3">
              <Activity
                size={23}
                className="text-[#826049]"
              />

              <h2 className="font-serif text-xl font-semibold">
                Distribusi Prioritas
              </h2>
            </div>

            <p className="mt-2 text-sm text-[#817769]">
              Jumlah tugas berdasarkan tingkat prioritas.
            </p>

            <div className="mt-9 space-y-7">
              {priorityData.map((item) => {
                const percentage = stats.total
                  ? (item.value / stats.total) * 100
                  : 0;

                return (
                  <div key={item.label}>
                    <div className="mb-3 flex items-center justify-between text-sm">
                      <span className="font-medium">
                        {item.label}
                      </span>

                      <span className="text-[#817769]">
                        {item.value} tugas
                      </span>
                    </div>

                    <div className="h-4 overflow-hidden rounded-full bg-[#EEE8DE]">
                      <div
                        className="h-full rounded-full transition-all"
                        style={{
                          width: `${percentage}%`,
                          backgroundColor: item.color,
                        }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>

            <p className="mt-9 text-xs text-[#9A8F81]">
              Distribusi dihitung dari seluruh tugas,
              termasuk yang sudah selesai.
            </p>
          </div>
        </section>

        {/* DEADLINE AND PRIORITIES */}
        <section className="mt-8 grid gap-6 xl:grid-cols-2">
          {/* DEADLINE SUMMARY */}
          <div className="rounded-2xl border border-[#E9DED0] bg-[#FFF9F0] p-7 shadow-sm">
            <div className="flex items-center gap-3">
              <CalendarClock
                size={23}
                className="text-[#826049]"
              />

              <h2 className="font-serif text-xl font-semibold">
                Ringkasan Deadline
              </h2>
            </div>

            <div className="mt-7 space-y-4">
              <div className="flex items-center justify-between rounded-xl bg-[#F8E7E3] p-5">
                <div className="flex items-center gap-3">
                  <AlertTriangle
                    size={22}
                    className="text-[#A64C43]"
                  />

                  <div>
                    <p className="font-semibold text-[#75423C]">
                      Terlambat
                    </p>

                    <p className="mt-1 text-xs text-[#946B65]">
                      Deadline sudah lewat
                    </p>
                  </div>
                </div>

                <span className="text-3xl font-bold text-[#A64C43]">
                  {stats.overdue}
                </span>
              </div>

              <div className="flex items-center justify-between rounded-xl bg-[#E8EFE5] p-5">
                <div className="flex items-center gap-3">
                  <CalendarClock
                    size={22}
                    className="text-[#55724E]"
                  />

                  <div>
                    <p className="font-semibold text-[#55724E]">
                      7 Hari ke Depan
                    </p>

                    <p className="mt-1 text-xs text-[#71816B]">
                      Termasuk deadline hari ini
                    </p>
                  </div>
                </div>

                <span className="text-3xl font-bold text-[#55724E]">
                  {stats.upcoming}
                </span>
              </div>
            </div>
          </div>

          {/* HIGH PRIORITY TASKS */}
          <div className="rounded-2xl border border-[#E9DED0] bg-[#FFF9F0] p-7 shadow-sm">
            <div className="flex items-center gap-3">
              <AlertTriangle
                size={23}
                className="text-[#C98076]"
              />

              <h2 className="font-serif text-xl font-semibold">
                Prioritas Utama
              </h2>
            </div>

            <p className="mt-2 text-sm text-[#817769]">
              Maksimal 5 tugas prioritas tinggi
              yang belum selesai.
            </p>

            <div className="mt-6 space-y-3">
              {stats.highPriorityTasks.length === 0 ? (
                <div className="rounded-xl border border-dashed border-[#DDD2C3] bg-white p-6 text-center">
                  <CheckCircle2
                    size={28}
                    className="mx-auto text-[#8D9B80]"
                  />

                  <p className="mt-3 text-sm text-[#817769]">
                    Tidak ada tugas prioritas tinggi
                    yang belum selesai.
                  </p>
                </div>
              ) : (
                stats.highPriorityTasks.map((task) => (
                  <div
                    key={task.id}
                    className="rounded-xl border border-[#E9DED0] bg-white p-4"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <p className="break-words text-sm font-medium text-[#45453D]">
                        {task.title}
                      </p>

                      <span className="shrink-0 rounded-full bg-[#F5DDDA] px-2.5 py-1 text-xs font-medium text-[#A64C43]">
                        {priorityLabels.High}
                      </span>
                    </div>

                    <p className="mt-2 text-xs text-[#817769]">
                      Deadline: {formatDeadline(task.deadline)}
                    </p>
                  </div>
                ))
              )}
            </div>
          </div>
        </section>

        <footer className="mt-10 text-center text-xs text-[#A49A8C]">
          GradaTim — Plan, Focus, Achieve
        </footer>
      </div>
    </DashboardLayout>
  );
}

function StatCard({
  label,
  value,
  icon,
}: {
  label: string;
  value: number | string;
  icon: React.ReactNode;
}) {
  return (
    <div className="flex items-center justify-between rounded-2xl border border-[#E9DED0] bg-white p-6 shadow-sm">
      <div>
        <p className="text-sm text-[#817769]">
          {label}
        </p>

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

function Legend({
  color,
  label,
}: {
  color: string;
  label: string;
}) {
  return (
    <span className="flex items-center gap-2 text-[#817769]">
      <span
        className="h-3 w-3 rounded-full"
        style={{ backgroundColor: color }}
      />

      {label}
    </span>
  );
}
