"use client";

import { useMemo, type ReactNode } from "react";
import Link from "next/link";
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
import UserAvatar from "../../components/UserAvatar";
import { errorBoxClass } from "../../components/ui";
import { LEVEL, statistikTask, type Level } from "../../lib/analitik";
import { useTasks } from "../../lib/api/queries";
import { labelLevel } from "../../lib/label";
import { formatTanggal, hariIniWib } from "../../lib/waktu";

const warnaLevel: Record<Level, string> = {
  high: "#C98076",
  medium: "#C9A36D",
  low: "#8D9B80",
};

function formatDeadline(value: string | null) {
  if (!value) return "Tanpa deadline";
  return formatTanggal(value, { day: "numeric", month: "short", year: "numeric" });
}

function DistribusiLevel({
  judul,
  keterangan,
  ikon,
  data,
  total,
}: {
  judul: string;
  keterangan: string;
  ikon: ReactNode;
  data: Record<Level, number> & { lainnya: number };
  total: number;
}) {
  return (
    <div className="rounded-2xl border border-[#E9DED0] bg-white p-7 shadow-sm">
      <div className="flex items-center gap-3">
        {ikon}
        <h2 className="font-serif text-xl font-semibold">{judul}</h2>
      </div>
      <p className="mt-2 text-sm text-[#817769]">{keterangan}</p>

      <div className="mt-9 space-y-7">
        {LEVEL.map((level) => {
          const nilai = data[level];
          const persen = total ? (nilai / total) * 100 : 0;
          return (
            <div key={level}>
              <div className="mb-3 flex items-center justify-between text-sm">
                <span className="font-medium">{labelLevel(level)}</span>
                <span className="text-[#817769]">{nilai} task</span>
              </div>
              <div className="h-4 overflow-hidden rounded-full bg-[#EEE8DE]">
                <div
                  className="h-full rounded-full transition-all"
                  style={{ width: `${persen}%`, backgroundColor: warnaLevel[level] }}
                />
              </div>
            </div>
          );
        })}
      </div>

      {data.lainnya > 0 && (
        <p className="mt-6 text-xs text-[#9A8F81]">{data.lainnya} task belum punya penilaian.</p>
      )}
    </div>
  );
}

export default function AnalyticsPage() {
  const tasks = useTasks();
  const hariIni = hariIniWib();
  const stats = useMemo(() => statistikTask(tasks.data ?? [], hariIni), [tasks.data, hariIni]);

  return (
    <DashboardLayout>
      <div className="mx-auto max-w-6xl">
        {/* HEADER */}
        <header className="flex items-start justify-between gap-4">
          <div>
            <p className="text-sm text-[#8A7A69]">Personal Productivity Planner</p>
            <h1 className="mt-2 font-serif text-4xl font-semibold">Analitik</h1>
            <p className="mt-3 text-sm text-[#817769]">
              Pantau perkembangan task dari semua goal-mu dan kenali yang perlu didahulukan.
            </p>
          </div>
          <UserAvatar />
        </header>

        {tasks.isError && (
          <p role="alert" className={`mt-6 ${errorBoxClass}`}>
            {tasks.error.message}
          </p>
        )}
        {tasks.isPending && <p className="mt-6 text-sm text-[#8B857B]">Memuat data...</p>}

        {tasks.isSuccess && stats.total === 0 && (
          <div className="mt-8 rounded-2xl border border-dashed border-[#DDD2C3] bg-white p-8 text-center">
            <p className="font-medium">Belum ada task</p>
            <p className="mt-1 text-sm text-[#817769]">
              Task dibuat oleh AI dari goal-mu.{" "}
              <Link href="/planning/step-1" className="font-medium text-[#506851] underline">
                Buat rencana pertama
              </Link>
            </p>
          </div>
        )}

        {tasks.isSuccess && stats.total > 0 && (
          <>
            {/* SUMMARY CARDS */}
            <section className="mt-9 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
              <StatCard label="Total Task" value={stats.total} icon={<ListTodo size={22} />} />
              <StatCard label="Selesai" value={stats.selesai} icon={<CheckCircle2 size={22} />} />
              <StatCard label="Sedang Dikerjakan" value={stats.sedang} icon={<Activity size={22} />} />
              <StatCard label="Belum Mulai" value={stats.belum} icon={<Circle size={22} />} />
            </section>

            {/* CHARTS */}
            <section className="mt-8 grid gap-6 xl:grid-cols-2">
              {/* COMPLETION CHART */}
              <div className="rounded-2xl border border-[#E9DED0] bg-white p-7 shadow-sm">
                <div className="flex items-center gap-3">
                  <Target size={23} className="text-[#64765C]" />
                  <h2 className="font-serif text-xl font-semibold">Penyelesaian Task</h2>
                </div>
                <p className="mt-2 text-sm text-[#817769]">Perbandingan task selesai dan belum selesai.</p>

                <div className="mt-9 flex flex-col items-center">
                  <div
                    role="img"
                    aria-label={`${stats.persenSelesai}% task selesai`}
                    className="relative flex h-48 w-48 items-center justify-center rounded-full"
                    style={{
                      background: `conic-gradient(#8D9B80 0% ${stats.persenSelesai}%, #EEE8DE ${stats.persenSelesai}% 100%)`,
                    }}
                  >
                    <div className="flex h-36 w-36 flex-col items-center justify-center rounded-full bg-white">
                      <span className="text-4xl font-bold text-[#64765C]">{stats.persenSelesai}%</span>
                      <span className="mt-1 text-xs text-[#817769]">Selesai</span>
                    </div>
                  </div>

                  <div className="mt-8 flex flex-wrap justify-center gap-5 text-sm">
                    <Legend color="#8D9B80" label={`Selesai (${stats.selesai})`} />
                    <Legend color="#EEE8DE" label={`Belum selesai (${stats.total - stats.selesai})`} />
                  </div>
                </div>
              </div>

              <DistribusiLevel
                judul="Distribusi Impact"
                keterangan="Jumlah task berdasarkan dampaknya terhadap goal (dinilai AI)."
                ikon={<TrendingUp size={23} className="text-[#826049]" />}
                data={stats.impact}
                total={stats.total}
              />
            </section>

            <section className="mt-6 grid gap-6 xl:grid-cols-2">
              <DistribusiLevel
                judul="Distribusi Effort"
                keterangan="Jumlah task berdasarkan beratnya usaha yang dibutuhkan."
                ikon={<Activity size={23} className="text-[#826049]" />}
                data={stats.effort}
                total={stats.total}
              />

              {/* DEADLINE SUMMARY */}
              <div className="rounded-2xl border border-[#E9DED0] bg-[#FFF9F0] p-7 shadow-sm">
                <div className="flex items-center gap-3">
                  <CalendarClock size={23} className="text-[#826049]" />
                  <h2 className="font-serif text-xl font-semibold">Ringkasan Deadline</h2>
                </div>

                <div className="mt-7 space-y-4">
                  <div className="flex items-center justify-between rounded-xl bg-[#F8E7E3] p-5">
                    <div className="flex items-center gap-3">
                      <AlertTriangle size={22} className="text-[#A64C43]" />
                      <div>
                        <p className="font-semibold text-[#75423C]">Terlambat</p>
                        <p className="mt-1 text-xs text-[#946B65]">Belum selesai, deadline sudah lewat</p>
                      </div>
                    </div>
                    <span className="text-3xl font-bold text-[#A64C43]">{stats.terlambat}</span>
                  </div>

                  <div className="flex items-center justify-between rounded-xl bg-[#E8EFE5] p-5">
                    <div className="flex items-center gap-3">
                      <CalendarClock size={22} className="text-[#55724E]" />
                      <div>
                        <p className="font-semibold text-[#55724E]">7 Hari ke Depan</p>
                        <p className="mt-1 text-xs text-[#71816B]">Termasuk deadline hari ini</p>
                      </div>
                    </div>
                    <span className="text-3xl font-bold text-[#55724E]">{stats.tujuhHari}</span>
                  </div>
                </div>
              </div>
            </section>

            {/* PRIORITAS UTAMA */}
            <section className="mt-6 rounded-2xl border border-[#E9DED0] bg-[#FFF9F0] p-7 shadow-sm">
              <div className="flex items-center gap-3">
                <AlertTriangle size={23} className="text-[#C98076]" />
                <h2 className="font-serif text-xl font-semibold">Prioritas Utama</h2>
              </div>
              <p className="mt-2 text-sm text-[#817769]">
                Maksimal 5 task berdampak tinggi yang belum selesai, deadline terdekat lebih dulu.
              </p>

              <div className="mt-6 grid gap-3 md:grid-cols-2">
                {stats.prioritasUtama.length === 0 ? (
                  <div className="rounded-xl border border-dashed border-[#DDD2C3] bg-white p-6 text-center md:col-span-2">
                    <CheckCircle2 size={28} className="mx-auto text-[#8D9B80]" />
                    <p className="mt-3 text-sm text-[#817769]">Tidak ada task berdampak tinggi yang belum selesai.</p>
                  </div>
                ) : (
                  stats.prioritasUtama.map((task) => (
                    <div key={task.id_task} className="rounded-xl border border-[#E9DED0] bg-white p-4">
                      <div className="flex items-start justify-between gap-3">
                        <p className="break-words text-sm font-medium text-[#45453D]">{task.nama_task}</p>
                        <span className="shrink-0 rounded-full bg-[#F5DDDA] px-2.5 py-1 text-xs font-medium text-[#A64C43]">
                          Impact {labelLevel(task.tingkat_impact)}
                        </span>
                      </div>
                      <p className="mt-2 text-xs text-[#817769]">
                        Deadline: {formatDeadline(task.deadline)} · Effort {labelLevel(task.tingkat_effort)}
                      </p>
                    </div>
                  ))
                )}
              </div>
            </section>
          </>
        )}

        <footer className="mt-10 text-center text-xs text-[#A49A8C]">GradaTim — Plan, Focus, Achieve</footer>
      </div>
    </DashboardLayout>
  );
}

function StatCard({ label, value, icon }: { label: string; value: number | string; icon: ReactNode }) {
  return (
    <div className="flex items-center justify-between rounded-2xl border border-[#E9DED0] bg-white p-6 shadow-sm">
      <div>
        <p className="text-sm text-[#817769]">{label}</p>
        <p className="mt-2 text-3xl font-bold text-[#30312B]">{value}</p>
      </div>
      <div className="rounded-xl bg-[#E8EFE5] p-3 text-[#64765C]">{icon}</div>
    </div>
  );
}

function Legend({ color, label }: { color: string; label: string }) {
  return (
    <span className="flex items-center gap-2 text-[#817769]">
      <span className="h-3 w-3 rounded-full" style={{ backgroundColor: color }} />
      {label}
    </span>
  );
}
