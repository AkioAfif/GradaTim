
"use client";

import { useState } from "react";
import {
  CalendarDays,
  ChevronLeft,
  ChevronRight,
  CheckCircle2,
  Clock3,
  ListTodo,
} from "lucide-react";

import DashboardLayout from "../../components/DashboardLayout";
import { useTasks } from "../../context/TaskContext";

const weekDays = ["Min", "Sen", "Sel", "Rab", "Kam", "Jum", "Sab"];

function toDateKey(date: Date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");

  return `${year}-${month}-${day}`;
}

function formatDate(date: Date) {
  return date.toLocaleDateString("id-ID", {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}

export default function CalendarPage() {
  const { tasks, toggleTask } = useTasks();

  const [selectedDate, setSelectedDate] = useState(
    () => new Date()
  );

  const [currentMonth, setCurrentMonth] = useState(
    () => new Date()
  );

  const year = currentMonth.getFullYear();
  const month = currentMonth.getMonth();

  const firstDay = new Date(year, month, 1).getDay();
  const daysInMonth = new Date(year, month + 1, 0).getDate();

  const calendarCells: (number | null)[] = [
    ...Array.from({ length: firstDay }, () => null),
    ...Array.from(
      { length: daysInMonth },
      (_, index) => index + 1
    ),
  ];

  const selectedKey = toDateKey(selectedDate);
  const todayKey = toDateKey(new Date());

  const selectedTasks = tasks.filter(
    (task) => task.deadline === selectedKey
  );

  const tasksWithDeadline = tasks.filter(
    (task) => Boolean(task.deadline)
  );

  const completedCount = tasksWithDeadline.filter(
    (task) => task.completed
  ).length;

  function changeMonth(offset: number) {
    const nextMonth = new Date(year, month + offset, 1);

    setCurrentMonth(nextMonth);
    setSelectedDate(nextMonth);
  }

  function selectDay(day: number) {
    setSelectedDate(new Date(year, month, day));
  }

  function goToToday() {
    const today = new Date();

    setCurrentMonth(today);
    setSelectedDate(today);
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
              Kalender
            </h1>

            <p className="mt-3 text-sm text-[#817769]">
              Pantau deadline dan atur aktivitasmu
              dengan lebih terencana.
            </p>
          </div>

          <button
            type="button"
            onClick={goToToday}
            className="rounded-xl bg-[#826049] px-5 py-3 text-sm font-semibold text-white hover:bg-[#6D4D38]"
          >
            Hari Ini
          </button>
        </header>

        {/* SUMMARY */}
        <section className="mt-9 grid gap-4 sm:grid-cols-3">
          <SummaryCard
            label="Tugas dengan Deadline"
            value={tasksWithDeadline.length}
            icon={<CalendarDays size={22} />}
          />

          <SummaryCard
            label="Belum Selesai"
            value={tasksWithDeadline.length - completedCount}
            icon={<Clock3 size={22} />}
          />

          <SummaryCard
            label="Selesai"
            value={completedCount}
            icon={<CheckCircle2 size={22} />}
          />
        </section>

        <section className="mt-8 grid gap-6 xl:grid-cols-[1.5fr_1fr]">
          {/* CALENDAR */}
          <div className="rounded-2xl border border-[#E9DED0] bg-white p-5 shadow-sm sm:p-7">
            <div className="mb-7 flex items-center justify-between gap-3">
              <h2 className="font-serif text-2xl font-semibold capitalize">
                {currentMonth.toLocaleDateString("id-ID", {
                  month: "long",
                  year: "numeric",
                })}
              </h2>

              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => changeMonth(-1)}
                  aria-label="Bulan sebelumnya"
                  className="rounded-lg border border-[#E5D9C9] p-2 text-[#64765C] hover:bg-[#EEF1EB]"
                >
                  <ChevronLeft size={20} />
                </button>

                <button
                  type="button"
                  onClick={() => changeMonth(1)}
                  aria-label="Bulan berikutnya"
                  className="rounded-lg border border-[#E5D9C9] p-2 text-[#64765C] hover:bg-[#EEF1EB]"
                >
                  <ChevronRight size={20} />
                </button>
              </div>
            </div>

            <div className="grid grid-cols-7 gap-2">
              {weekDays.map((day) => (
                <div
                  key={day}
                  className="py-2 text-center text-xs font-semibold text-[#817769]"
                >
                  {day}
                </div>
              ))}

              {calendarCells.map((day, index) => {
                if (day === null) {
                  return (
                    <div
                      key={`empty-${index}`}
                      className="min-h-16"
                    />
                  );
                }

                const date = new Date(year, month, day);
                const dateKey = toDateKey(date);

                const dayTasks = tasks.filter(
                  (task) => task.deadline === dateKey
                );

                const isSelected = dateKey === selectedKey;
                const isToday = dateKey === todayKey;

                return (
                  <button
                    key={dateKey}
                    type="button"
                    onClick={() => selectDay(day)}
                    aria-label={`${formatDate(date)}, ${dayTasks.length} tugas`}
                    aria-pressed={isSelected}
                    className={`flex min-h-16 flex-col items-center justify-center gap-2 rounded-xl border p-2 transition ${
                      isSelected
                        ? "border-[#64765C] bg-[#E8EFE5]"
                        : isToday
                          ? "border-[#D6B99B] bg-[#FFF5E8]"
                          : "border-transparent hover:border-[#E5D9C9] hover:bg-[#FAF6EE]"
                    }`}
                  >
                    <span
                      className={`text-sm font-semibold ${
                        isSelected
                          ? "text-[#55724E]"
                          : "text-[#45453D]"
                      }`}
                    >
                      {day}
                    </span>

                    {dayTasks.length > 0 ? (
                      <span className="flex items-center gap-1">
                        {dayTasks.slice(0, 3).map((task) => (
                          <span
                            key={task.id}
                            className={`h-1.5 w-1.5 rounded-full ${
                              task.completed
                                ? "bg-[#8D9B80]"
                                : "bg-[#C38D64]"
                            }`}
                          />
                        ))}
                      </span>
                    ) : (
                      <span className="h-1.5" />
                    )}
                  </button>
                );
              })}
            </div>

            <div className="mt-7 flex flex-wrap gap-5 border-t border-[#EEE8DE] pt-5 text-xs text-[#817769]">
              <span className="flex items-center gap-2">
                <span className="h-2.5 w-2.5 rounded-full bg-[#C38D64]" />
                Belum selesai
              </span>

              <span className="flex items-center gap-2">
                <span className="h-2.5 w-2.5 rounded-full bg-[#8D9B80]" />
                Selesai
              </span>
            </div>
          </div>

          {/* SELECTED DATE TASKS */}
          <div className="rounded-2xl border border-[#E9DED0] bg-[#FFF9F0] p-5 shadow-sm sm:p-7">
            <div className="flex items-center gap-3">
              <ListTodo size={23} className="text-[#826049]" />

              <h2 className="font-serif text-xl font-semibold">
                Jadwal Tugas
              </h2>
            </div>

            <p className="mt-3 text-sm capitalize text-[#817769]">
              {formatDate(selectedDate)}
            </p>

            <div className="mt-6 space-y-3">
              {selectedTasks.length === 0 ? (
                <div className="rounded-xl border border-dashed border-[#DDD2C3] bg-white p-6 text-center">
                  <CalendarDays
                    size={28}
                    className="mx-auto text-[#A49A8C]"
                  />

                  <p className="mt-3 text-sm font-medium">
                    Belum ada deadline
                  </p>

                  <p className="mt-2 text-xs leading-5 text-[#817769]">
                    Pilih tanggal lain atau tambahkan
                    deadline melalui halaman Tugas.
                  </p>
                </div>
              ) : (
                selectedTasks.map((task) => (
                  <label
                    key={task.id}
                    className="flex cursor-pointer items-start gap-3 rounded-xl border border-[#E9DED0] bg-white p-4"
                  >
                    <input
                      type="checkbox"
                      checked={task.completed}
                      onChange={() => toggleTask(task.id)}
                      className="mt-1 h-4 w-4 accent-[#64765C]"
                    />

                    <div className="min-w-0">
                      <p
                        className={`break-words text-sm font-medium ${
                          task.completed
                            ? "text-[#A49A8C] line-through"
                            : "text-[#45453D]"
                        }`}
                      >
                        {task.title}
                      </p>

                      <p className="mt-1 text-xs text-[#817769]">
                        Prioritas:{" "}
                        {task.priority === "High"
                          ? "Tinggi"
                          : task.priority === "Medium"
                            ? "Sedang"
                            : "Rendah"}
                      </p>
                    </div>
                  </label>
                ))
              )}
            </div>

            <p className="mt-6 text-xs text-[#9A8F81]">
              {selectedTasks.length} tugas pada tanggal ini.
            </p>
          </div>
        </section>

        <footer className="mt-10 text-center text-xs text-[#A49A8C]">
          GradaTim — Plan, Focus, Achieve
        </footer>
      </div>
    </DashboardLayout>
  );
}

function SummaryCard({
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
