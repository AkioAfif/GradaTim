"use client";

import { useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";

import { useAuth } from "../../context/AuthContext";
import { susunUlang } from "../../lib/api/jadwal";
import { invalidateJadwal } from "../../lib/api/queries";
import { hariIniWib } from "../../lib/waktu";

/**
 * POST /jadwal/susun-ulang sekali per tab per hari saat aplikasi dibuka (FR-11): sesi yang terlewat
 * tanpa konfirmasi berubah menjadi `tidak_diketahui` (muncul di "perlu dikonfirmasi") dan task-nya
 * dijadwalkan ulang. Tanpa ini, sesi terlewat tetap `terjadwal` dan tidak pernah dijadwalkan ulang.
 */
export function useSusunUlangOtomatis() {
  const { status, user } = useAuth();
  const queryClient = useQueryClient();
  const idUser = user?.id_user;

  useEffect(() => {
    if (status !== "authenticated" || idUser == null) return;

    const kunci = `gradatim-susun-ulang:${idUser}:${hariIniWib()}`;
    try {
      if (sessionStorage.getItem(kunci)) return;
      // dipasang sebelum request: StrictMode (dev) menjalankan efek dua kali
      sessionStorage.setItem(kunci, "1");
    } catch {
      // tanpa sessionStorage tetap jalan (paling banyak sekali per muat halaman)
    }

    susunUlang({})
      .then(() => invalidateJadwal(queryClient))
      .catch((error) => {
        console.error("Susun ulang otomatis gagal:", error);
        try {
          sessionStorage.removeItem(kunci); // coba lagi saat halaman berikutnya dibuka
        } catch {
          // abaikan
        }
      });
  }, [status, idUser, queryClient]);
}
