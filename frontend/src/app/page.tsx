"use client";

import { useState } from "react";
import Link from "next/link";
import { Bell, Plus, Search } from "lucide-react";

import DashboardLayout from "../components/DashboardLayout";
import UserAvatar from "../components/UserAvatar";
import KotakPerluKonfirmasi from "../components/jadwal/KotakPerluKonfirmasi";
import SesiCard from "../components/jadwal/SesiCard";
import { useSekarang } from "../components/jadwal/hooks";
import BannerMood from "../components/mood/BannerMood";
import { errorBoxClass } from "../components/ui";
import { useAuth } from "../context/AuthContext";
import { useGoals, useJadwalMinggu, useMoodHariIni, useTasks } from "../lib/api/queries";
import type { GoalRead } from "../lib/api/types";
import { ringkasanPerHari, sesiBerikutnyaHariIni, sesiPadaTanggal, sesiPerluKonfirmasi } from "../lib/sesi";
import {
  NAMA_HARI,
  awalMinggu,
  formatTanggal,
  hariDalamMinggu,
  hariIniWib,
  hariSeminggu,
  tambahHari,
  tanggalDari,
} from "../lib/waktu";
import { selisihHari } from "../lib/kalender";

function persen(bagian: number, total: number): number {
  return total > 0 ? Math.round((bagian / total) * 100) : 0;
}

function KartuGoal({ goal, hariIni }: { goal: GoalRead; hariIni: string }) {
  const sisaHari = goal.deadline ? selisihHari(hariIni, tanggalDari(goal.deadline)) : null;
  return (
    <Link
      href={`/goals/${goal.id_goal}`}
      className="block rounded-xl border border-[#E7DBCC] bg-[#FFFCF7] p-5 transition hover:border-[#82947B] hover:shadow-sm"
    >
      <p className="font-medium text-[#30312B]">{goal.judul_goal}</p>
      {goal.deadline && (
        <p className="mt-2 text-xs text-[#8B857B]">
          Deadline {formatTanggal(goal.deadline, { day: "numeric", month: "short", year: "numeric" })}
          {sisaHari !== null &&
            (sisaHari > 0 ? ` · ${sisaHari} hari lagi` : sisaHari === 0 ? " · hari ini" : " · sudah lewat")}
        </p>
      )}
      <p className="mt-3 text-xs font-medium text-[#506851]">Lihat rencana →</p>
    </Link>
  );
}

export default function Home() {
  const { user } = useAuth();
  const sekarang = useSekarang();
  const hariIni = hariIniWib();
  const senin = awalMinggu(hariIni);
  const [cari, setCari] = useState("");

  const jadwal = useJadwalMinggu(senin);
  // jendela konfirmasi 48 jam bisa melewati batas minggu: Senin/Selasa ikut cek minggu lalu
  const butuhMingguLalu = hariDalamMinggu(hariIni) <= 1;
  const jadwalLalu = useJadwalMinggu(tambahHari(senin, -7), butuhMingguLalu);
  const tasks = useTasks();
  const goals = useGoals();
  const mood = useMoodHariIni();

  const sesiMingguIni = jadwal.data?.sesi ?? [];
  const perluKonfirmasi = sesiPerluKonfirmasi(
    [...(butuhMingguLalu ? jadwalLalu.data?.sesi ?? [] : []), ...sesiMingguIni],
    sekarang
  );

  const kataKunci = cari.trim().toLowerCase();
  const cocok = (teks: string) => !kataKunci || teks.toLowerCase().includes(kataKunci);
  const sesiHariIni = sesiPadaTanggal(sesiMingguIni, hariIni).filter((s) => cocok(s.nama_task));
  const daftarGoal = (goals.data ?? []).filter((g) => cocok(g.judul_goal));

  const sesiSelesai = sesiMingguIni.filter((s) => s.status === "selesai").length;
  const taskSelesai = (tasks.data ?? []).filter((t) => t.status === "done").length;
  const totalTask = tasks.data?.length ?? 0;
  const progresSesi = persen(sesiSelesai, sesiMingguIni.length);
  const ringkasan = ringkasanPerHari(sesiMingguIni, hariSeminggu(hariIni));
  const namaDepan = user?.nama.trim().split(/\s+/)[0];

  return (
    <DashboardLayout>
      <div className="mx-auto max-w-5xl">
        {/* TOP BAR */}
        <header className="flex items-center justify-between gap-4 border-b border-[#E9E0D4] pb-5">
          <div className="flex min-w-0 items-center gap-2 rounded-lg border border-[#E5DCD0] bg-white px-3 py-2">
            <Search size={15} className="shrink-0 text-[#8B857B]" />
            <input
              value={cari}
              onChange={(event) => setCari(event.target.value)}
              placeholder="Cari goal atau task hari ini..."
              aria-label="Cari goal atau task hari ini"
              className="w-48 min-w-0 bg-transparent text-xs outline-none sm:w-64"
            />
          </div>

          <div className="flex items-center gap-5">
            <a
              href={perluKonfirmasi.length > 0 ? "#perlu-konfirmasi" : undefined}
              aria-label={`${perluKonfirmasi.length} sesi perlu dikonfirmasi`}
              title={`${perluKonfirmasi.length} sesi perlu dikonfirmasi`}
              className="relative text-[#8B857B]"
            >
              <Bell size={17} />
              {perluKonfirmasi.length > 0 && (
                <span className="absolute -right-2 -top-2 flex h-4 min-w-4 items-center justify-center rounded-full bg-[#C9822B] px-1 text-[10px] font-semibold text-white">
                  {perluKonfirmasi.length}
                </span>
              )}
            </a>
            <UserAvatar />
          </div>
        </header>

        {/* WELCOME + CREATE PLAN BUTTON */}
        <section className="mt-7">
          <div className="flex flex-col gap-5 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="text-xs font-bold tracking-[0.12em] text-[#506851]">DASHBOARD</p>
              <h1 className="mt-3 text-3xl font-medium tracking-tight text-[#30312B] md:text-4xl">
                {namaDepan ? `Halo, ${namaDepan}!` : "Selamat datang kembali!"}
              </h1>
              <p className="mt-3 text-sm text-[#8B857B]">
                {formatTanggal(hariIni)} · Wujudkan targetmu, satu langkah kecil setiap waktu.
              </p>
            </div>

            <Link
              href="/planning/step-1"
              className="inline-flex shrink-0 items-center justify-center gap-2 self-start rounded-xl bg-[#826049] px-5 py-3 text-sm font-medium text-white transition-colors hover:bg-[#6D4D38]"
            >
              <Plus size={18} />
              Buat Rencana Baru
            </Link>
          </div>
        </section>

        {/* PERLU KONFIRMASI (label model) + MOOD */}
        <div className="mt-7 space-y-4">
          <KotakPerluKonfirmasi id="perlu-konfirmasi" sesi={perluKonfirmasi} sekarang={sekarang} />
          <BannerMood
            mood={mood.data}
            memuat={mood.isPending}
            sesiBerikutnya={sesiBerikutnyaHariIni(sesiMingguIni, hariIni, sekarang)}
          />
          {jadwal.isError && (
            <p role="alert" className={errorBoxClass}>
              Gagal memuat jadwal: {jadwal.error.message}
            </p>
          )}
        </div>

        {/* STATISTICS */}
        <section className="mt-7 grid gap-4 md:grid-cols-2">
          <div className="rounded-xl bg-[#F3EADD] p-6">
            <p className="text-sm text-[#8B857B]">Sesi Minggu Ini</p>
            <p className="mt-3 text-3xl font-bold text-[#506851]">{progresSesi}%</p>
            <div className="mt-3 h-3 overflow-hidden rounded-full bg-[#EAE3D9]">
              <div
                className="h-full rounded-full bg-[#82947B] transition-all"
                style={{ width: `${progresSesi}%` }}
              />
            </div>
            <p className="mt-3 text-xs text-[#8B857B]">
              {sesiSelesai} dari {sesiMingguIni.length} sesi selesai
            </p>
          </div>

          <div className="rounded-xl bg-[#F3EADD] p-6">
            <p className="text-sm text-[#8B857B]">Task Selesai</p>
            <p className="mt-3 text-3xl font-bold text-[#506851]">
              {taskSelesai} dari {totalTask}
            </p>
            <p className="mt-3 text-xs text-[#8B857B]">Dari semua goal-mu. Terus pertahankan konsistensimu!</p>
          </div>
        </section>

        {/* MAIN CARDS */}
        <section className="mt-4 grid gap-4 md:grid-cols-2">
          {/* TODAY ACTION LIST */}
          <div className="min-w-0 rounded-xl border border-[#E7DBCC] bg-[#F7EEE3] p-5">
            <h2 className="text-base font-bold">Today Action List</h2>

            <div className="mt-5 space-y-3">
              {jadwal.isPending ? (
                <p className="text-sm text-[#8B857B]">Memuat...</p>
              ) : sesiHariIni.length === 0 ? (
                <p className="py-2 text-sm text-[#8B857B]">
                  {kataKunci ? "Tidak ada sesi yang cocok." : "Tidak ada sesi task hari ini."}
                </p>
              ) : (
                sesiHariIni.map((s) => <SesiCard key={s.id_jadwal} sesi={s} sekarang={sekarang} />)
              )}
            </div>

            <button
              type="button"
              disabled
              title="Belum didukung backend: task dibuat lewat rencana AI"
              className="mt-4 cursor-not-allowed text-sm text-[#B5AC9F]"
            >
              + Tambah tugas
            </button>
          </div>

          {/* WEEKLY VIEW */}
          <div className="rounded-xl border border-[#E7DBCC] bg-[#F7EEE3] p-5">
            <h2 className="text-base font-bold">Weekly View</h2>
            <p className="mt-3 text-sm text-[#8B857B]">Sesi task per hari minggu ini.</p>

            <div className="mt-5 space-y-2">
              {ringkasan.map((hari, indeks) => (
                <div
                  key={hari.tanggal}
                  className={`flex items-center justify-between rounded-lg border px-4 py-3 ${
                    hari.tanggal === hariIni ? "border-[#82947B] bg-[#EFF2EB]" : "border-[#E7DBCC] bg-[#FBF6EE]"
                  }`}
                >
                  <span className="text-sm">{NAMA_HARI[indeks]}</span>
                  <span className="text-sm text-[#64675E]">
                    {hari.total === 0 ? "—" : `${hari.selesai}/${hari.total} sesi selesai`}
                  </span>
                </div>
              ))}
            </div>

            <Link
              href="/calendar"
              className="mt-5 inline-flex rounded-lg bg-[#826049] px-5 py-3 text-sm font-medium text-white hover:bg-[#6D4D38]"
            >
              Lihat Mingguan →
            </Link>
          </div>
        </section>

        {/* RENCANA SAYA */}
        <section className="mt-8">
          <div className="flex items-center justify-between gap-4">
            <div>
              <h2 className="text-lg font-semibold">Rencana Saya</h2>
              <p className="mt-1 text-sm text-[#8B857B]">Goal yang sedang kamu kejar.</p>
            </div>
          </div>

          <div className="mt-4">
            {goals.isPending ? (
              <p className="text-sm text-[#8B857B]">Memuat...</p>
            ) : goals.isError ? (
              <p role="alert" className={errorBoxClass}>
                {goals.error.message}
              </p>
            ) : daftarGoal.length === 0 ? (
              <div className="rounded-xl border border-dashed border-[#D8CBB9] p-6 text-center">
                <p className="text-sm font-medium">
                  {kataKunci ? "Tidak ada goal yang cocok." : "Belum ada rencana"}
                </p>
                {!kataKunci && (
                  <p className="mt-1 text-sm text-[#8B857B]">
                    Klik <strong>Buat Rencana Baru</strong> untuk memecah goal pertamamu dengan AI.
                  </p>
                )}
              </div>
            ) : (
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {daftarGoal.map((g) => (
                  <KartuGoal key={g.id_goal} goal={g} hariIni={hariIni} />
                ))}
              </div>
            )}
          </div>
        </section>
      </div>
    </DashboardLayout>
  );
}
