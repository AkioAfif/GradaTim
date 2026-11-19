
"use client";

import { useState } from "react";
import Link from "next/link";
import {
  ChevronLeft,
  ChevronRight,
  CalendarDays,
} from "lucide-react";

import DashboardLayout from "../../components/DashboardLayout";
import { useTasks } from "../../context/TaskContext";

type ViewMode = "month" | "week";

const weekdays = ["Sen", "Sel", "Rab", "Kam", "Jum", "Sab", "Min"];

function toDateKey(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");

  return `${year}-${month}-${day}`;
}

function parseDateKey(key: string): Date {
  const [year, month, day] = key.split("-").map(Number);
  return new Date(year, month - 1, day);
}

function getMonday(date: Date): Date {
  const result = new Date(date);
  const offset = (result.getDay() + 6) % 7;
  result.setDate(result.getDate() - offset);
  return result;
}

function formatDate(date: Date): string {
  return date.toLocaleDateString("id-ID", {
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

  const [displayDate, setDisplayDate] = useState(
    () => new Date()
  );

  const [viewMode, setViewMode] = useState<ViewMode>("month");

  const todayKey = toDateKey(new Date());
  const selectedKey = toDateKey(selectedDate);

  const selectedTasks = tasks.filter(
    (task) => task.deadline === selectedKey
  );

  const sprintStart = getMonday(selectedDate);
  const sprintEnd = new Date(sprintStart);
  sprintEnd.setDate(sprintEnd.getDate() + 13);

  const sprintTasks = tasks.filter((task) => {
    if (!task.deadline) return false;

    const deadline = parseDateKey(task.deadline);

    return deadline >= sprintStart && deadline <= sprintEnd;
  });

  function changePeriod(direction: number) {
    const next = new Date(displayDate);

    if (viewMode === "month") {
      next.setDate(1);
      next.setMonth(next.getMonth() + direction);
    } else {
      next.setDate(next.getDate() + direction * 7);
    }

    setDisplayDate(next);
  }

  function selectDate(date: Date) {
    setSelectedDate(date);
    setDisplayDate(date);
  }

  function renderMonthDays() {
    const year = displayDate.getFullYear();
    const month = displayDate.getMonth();

    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);

    const offset = (firstDay.getDay() + 6) % 7;
    const totalDays = lastDay.getDate();

    const cells: (Date | null)[] = [];

    for (let index = 0; index < offset; index++) {
      cells.push(null);
    }

    for (let day = 1; day <= totalDays; day++) {
      cells.push(new Date(year, month, day));
    }

    while (cells.length % 7 !== 0) {
      cells.push(null);
    }

    return cells;
  }

  function renderWeekDays() {
    const monday = getMonday(displayDate);

    return Array.from({ length: 7 }, (_, index) => {
      const day = new Date(monday);
      day.setDate(monday.getDate() + index);
      return day;
    });
  }

  const visibleDays =
    viewMode === "month" ? renderMonthDays() : renderWeekDays();

  const periodTitle =
    viewMode === "month"
      ? displayDate.toLocaleDateString("id-ID", {
          month: "long",
          year: "numeric",
        })
      : `${formatDate(getMonday(displayDate))} - ${formatDate(
          (() => {
            const sunday = getMonday(displayDate);
            sunday.setDate(sunday.getDate() + 6);
            return sunday;
          })()
        )}`;

  return (
    <DashboardLayout>
      <div className="mx-auto max-w-5xl">
        {/* HEADER */}
        <header className="flex items-center justify-between border-b border-[#E9E0D4] pb-5">
          <p className="text-xs text-[#8B857B]">
            Kalender
          </p>

          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-[#D7B99B] text-sm font-medium text-white">
            A
          </div>
        </header>

        {/* TITLE */}
        <section className="mt-7 flex flex-wrap items-start justify-between gap-5">
          <div>
            <h1 className="text-3xl font-medium tracking-tight md:text-4xl">
              Kalender Belajar
            </h1>

            <p className="mt-3 text-sm text-[#8B857B]">
              Pantau jadwal dan targetmu dalam satu tampilan.
            </p>
          </div>

          <div className="flex items-center gap-3">
            {(["month", "week"] as ViewMode[]).map((mode) => (
              <button
                key={mode}
                type="button"
                onClick={() => setViewMode(mode)}
                className={`rounded-full px-5 py-2.5 text-sm transition ${
                  viewMode === mode
                    ? "bg-[#F0C4A4] text-[#45382E]"
                    : "bg-[#ECE9E1] text-[#57564F] hover:bg-[#E2DDD3]"
                }`}
              >
                {mode === "month" ? "Month" : "Week"}
              </button>
            ))}
          </div>
        </section>

        {/* CALENDAR + SPRINT */}
        <section className="mt-7 grid items-start gap-4 lg:grid-cols-[1.2fr_1fr]">
          {/* CALENDAR CARD */}
          <div className="rounded-xl border border-[#E7DBCC] bg-[#FFFCF7] p-5">
            <div className="mb-5 flex items-center justify-between gap-3">
              <h2 className="text-base font-semibold capitalize">
                {periodTitle}
              </h2>

              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => changePeriod(-1)}
                  aria-label="Periode sebelumnya"
                  className="rounded-lg p-2 hover:bg-[#F3EADD]"
                >
                  <ChevronLeft size={18} />
                </button>

                <button
                  type="button"
                  onClick={() => changePeriod(1)}
                  aria-label="Periode berikutnya"
                  className="rounded-lg p-2 hover:bg-[#F3EADD]"
                >
                  <ChevronRight size={18} />
                </button>
              </div>
            </div>

            <div className="grid grid-cols-7 gap-1">
              {weekdays.map((day) => (
                <div
                  key={day}
                  className="rounded-md border border-[#E9E0D4] bg-white py-3 text-center text-xs font-medium"
                >
                  {day}
                </div>
              ))}

              {visibleDays.map((date, index) => {
                if (!date) {
                  return (
                    <div
                      key={`empty-${index}`}
                      className="min-h-12"
                    />
                  );
                }

                const key = toDateKey(date);
                const isSelected = key === selectedKey;
                const isToday = key === todayKey;

                const taskCount = tasks.filter(
                  (task) => task.deadline === key
                ).length;

                return (
                  <button
                    key={key}
                    type="button"
                    onClick={() => selectDate(date)}
                    title={`${formatDate(date)} - ${taskCount} tugas`}
                    className={`relative flex min-h-12 flex-col items-center justify-center rounded-md border text-sm transition ${
                      isSelected
                        ? "border-[#826049] bg-[#826049] text-white"
                        : isToday
                        ? "border-[#82947B] bg-[#EFF2EB] text-[#506851]"
                        : "border-[#E9E0D4] bg-white hover:bg-[#F3EADD]"
                    }`}
                  >
                    <span>{date.getDate()}</span>

                    {taskCount > 0 && (
                      <span
                        className={`mt-1 h-1.5 w-1.5 rounded-full ${
                          isSelected
                            ? "bg-white"
                            : "bg-[#82947B]"
                        }`}
                      />
                    )}
                  </button>
                );
              })}
            </div>

            <div className="mt-5 border-t border-[#E9E0D4] pt-4">
              <p className="text-sm font-semibold">
                Tugas pada {formatDate(selectedDate)}
              </p>

              {selectedTasks.length === 0 ? (
                <p className="mt-3 text-sm text-[#8B857B]">
                  Belum ada tugas dengan deadline pada tanggal ini.
                </p>
              ) : (
                <div className="mt-3 space-y-3">
                  {selectedTasks.map((task) => (
                    <label
                      key={task.id}
                      className="flex cursor-pointer items-center gap-3 text-sm"
                    >
                      <input
                        type="checkbox"
                        checked={task.completed}
                        onChange={() => toggleTask(task.id)}
                        className="h-4 w-4 accent-[#82947B]"
                      />

                      <span
                        className={
                          task.completed
                            ? "text-[#A49A8C] line-through"
                            : ""
                        }
                      >
                        {task.title}
                      </span>
                    </label>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* SPRINT OVERVIEW */}
          <div className="rounded-xl border border-[#E7DBCC] bg-[#F7EEE3] p-5">
            <div className="flex items-center gap-2">
              <CalendarDays
                size={19}
                className="text-[#506851]"
              />

              <h2 className="text-base font-semibold">
                Sprint Overview
              </h2>
            </div>

            <p className="mt-3 text-xs text-[#8B857B]">
              {formatDate(sprintStart)} - {formatDate(sprintEnd)}
            </p>

            <p className="mt-2 text-xs text-[#8B857B]">
              Ringkasan tugas dalam periode 14 hari.
            </p>

            <div className="mt-5 divide-y divide-[#E9E0D4]">
              {sprintTasks.length === 0 ? (
                <p className="py-4 text-sm text-[#8B857B]">
                  Belum ada tugas untuk periode ini.
                </p>
              ) : (
                sprintTasks.map((task) => (
                  <label
                    key={task.id}
                    className="flex cursor-pointer items-center gap-3 py-3 text-sm"
                  >
                    <input
                      type="checkbox"
                      checked={task.completed}
                      onChange={() => toggleTask(task.id)}
                      className="h-4 w-4 accent-[#82947B]"
                    />

                    <span
                      className={
                        task.completed
                          ? "text-[#A49A8C] line-through"
                          : ""
                      }
                    >
                      {task.title}
                    </span>
                  </label>
                ))
              )}
            </div>

            <Link
              href="/tasks"
              className="mt-5 inline-block text-sm text-[#8B857B] hover:text-[#826049]"
            >
              Lihat detail →
            </Link>
          </div>
        </section>
      </div>
    </DashboardLayout>
  );
}
