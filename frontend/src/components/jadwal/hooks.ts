"use client";

import { useEffect, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import { toApiError, type ApiError } from "../../lib/api/client";
import { susunUlang, ubahSesi } from "../../lib/api/jadwal";
import { invalidateJadwal } from "../../lib/api/queries";
import type { HasilSusunUlangRead, SesiRead, SesiUpdate, SusunUlangRequest } from "../../lib/api/types";

/** Waktu sekarang, diperbarui tiap `intervalMs` — tombol konfirmasi muncul sendiri saat sesi mulai. */
export function useSekarang(intervalMs = 30_000): Date {
  const [sekarang, setSekarang] = useState(() => new Date());
  useEffect(() => {
    const timer = setInterval(() => setSekarang(new Date()), intervalMs);
    return () => clearInterval(timer);
  }, [intervalMs]);
  return sekarang;
}

/** PATCH /jadwal/sesi/{id}: konfirmasi status dan/atau pindah waktu. */
export function useUbahSesi() {
  const queryClient = useQueryClient();
  return useMutation<SesiRead, ApiError, { idJadwal: number; perubahan: SesiUpdate }>({
    mutationFn: async ({ idJadwal, perubahan }) => {
      try {
        return await ubahSesi(idJadwal, perubahan);
      } catch (err) {
        throw toApiError(err);
      }
    },
    // status task ikut dihitung ulang backend; rekomendasi mood dihitung dari jadwal
    onSettled: () => invalidateJadwal(queryClient),
  });
}

/** POST /jadwal/susun-ulang. */
export function useSusunUlang() {
  const queryClient = useQueryClient();
  return useMutation<HasilSusunUlangRead, ApiError, SusunUlangRequest | void>({
    mutationFn: async (payload) => {
      try {
        return await susunUlang(payload ?? {});
      } catch (err) {
        throw toApiError(err);
      }
    },
    onSuccess: () => invalidateJadwal(queryClient),
  });
}
