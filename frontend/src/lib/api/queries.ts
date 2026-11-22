"use client";

import { useQuery, type QueryClient } from "@tanstack/react-query";

import { useAuth } from "../../context/AuthContext";
import { ApiError, toApiError } from "./client";
import * as agendaApi from "./agenda";
import * as goalsApi from "./goals";
import * as jadwalApi from "./jadwal";
import * as moodApi from "./mood";
import * as tasksApi from "./tasks";
import * as timeConstraintsApi from "./timeConstraints";
import type { TanggalStr } from "./types";

// Kunci cache React Query. Awalan (elemen pertama) dipakai untuk invalidasi per domain.
export const queryKeys = {
  goals: ["goals"] as const,
  goal: (idGoal: number) => ["goal", idGoal] as const,
  tasks: (filter: tasksApi.TaskFilter = {}) => ["tasks", filter] as const,
  jadwal: (minggu: TanggalStr) => ["jadwal", minggu] as const,
  agenda: (mulai: TanggalStr, sampai: TanggalStr) => ["agenda", mulai, sampai] as const,
  moodHariIni: ["mood", "hari-ini"] as const,
  timeConstraints: ["time-constraints"] as const,
};

/**
 * Setelah jadwal berubah (konfirmasi/pindah sesi, susun ulang, jadwalkan, agenda, kegiatan rutin):
 * status task ikut dihitung ulang backend, dan rekomendasi mood dihitung dari jadwal saat request.
 */
export function invalidateJadwal(queryClient: QueryClient): Promise<void> {
  return Promise.all([
    queryClient.invalidateQueries({ queryKey: ["jadwal"] }),
    queryClient.invalidateQueries({ queryKey: ["agenda"] }),
    queryClient.invalidateQueries({ queryKey: ["tasks"] }),
    queryClient.invalidateQueries({ queryKey: ["goal"] }),
    queryClient.invalidateQueries({ queryKey: ["mood"] }),
  ]).then(() => undefined);
}

/** Setelah goal/milestone/task berubah (buat, dekomposisi, rinci minggu). */
export function invalidateGoals(queryClient: QueryClient): Promise<void> {
  return Promise.all([
    queryClient.invalidateQueries({ queryKey: ["goals"] }),
    queryClient.invalidateQueries({ queryKey: ["goal"] }),
    queryClient.invalidateQueries({ queryKey: ["tasks"] }),
  ]).then(() => undefined);
}

// Query hanya jalan setelah user terautentikasi, supaya tidak ada request tanpa token.
function useSiap(): boolean {
  return useAuth().status === "authenticated";
}

async function jalankan<T>(fn: () => Promise<T>): Promise<T> {
  try {
    return await fn();
  } catch (error) {
    throw toApiError(error);
  }
}

export function useGoals() {
  return useQuery({
    queryKey: queryKeys.goals,
    queryFn: () => jalankan(goalsApi.listGoals),
    enabled: useSiap(),
  });
}

export function useGoal(idGoal: number | null) {
  return useQuery({
    queryKey: queryKeys.goal(idGoal ?? 0),
    queryFn: () => jalankan(() => goalsApi.getGoal(idGoal as number)),
    enabled: useSiap() && idGoal != null,
  });
}

export function useTasks(filter: tasksApi.TaskFilter = {}) {
  return useQuery({
    queryKey: queryKeys.tasks(filter),
    queryFn: () => jalankan(() => tasksApi.listTasks(filter)),
    enabled: useSiap(),
  });
}

/** `minggu` = tanggal mana pun di minggu itu; dinormalkan pemanggil ke Senin agar cache tidak ganda. */
export function useJadwalMinggu(minggu: TanggalStr, enabled = true) {
  return useQuery({
    queryKey: queryKeys.jadwal(minggu),
    queryFn: () => jalankan(() => jadwalApi.getJadwalMinggu(minggu)),
    enabled: useSiap() && enabled,
  });
}

export function useAgenda(mulai: TanggalStr, sampai: TanggalStr) {
  return useQuery({
    queryKey: queryKeys.agenda(mulai, sampai),
    queryFn: () => jalankan(() => agendaApi.listAgenda({ mulai, sampai })),
    enabled: useSiap(),
  });
}

/** `data === null` = kuesioner hari ini belum diisi (404 dari backend). */
export function useMoodHariIni() {
  return useQuery({
    queryKey: queryKeys.moodHariIni,
    queryFn: () =>
      jalankan(async () => {
        try {
          return await moodApi.getMoodHariIni();
        } catch (error) {
          const apiError = toApiError(error);
          if (apiError.status === 404) return null;
          throw apiError;
        }
      }),
    enabled: useSiap(),
  });
}

export function useTimeConstraints() {
  return useQuery({
    queryKey: queryKeys.timeConstraints,
    queryFn: () => jalankan(timeConstraintsApi.listTimeConstraints),
    enabled: useSiap(),
  });
}

/** Pesan error siap tampil dari error query/mutasi apa pun. */
export function pesanError(error: unknown): string {
  return (error instanceof ApiError ? error : toApiError(error)).message;
}
