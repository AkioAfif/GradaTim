"use client";

import { useEffect, useState } from "react";

/** Detik sejak `aktif` menjadi true (indikator proses AI yang bisa beberapa menit). */
export function useDetikBerjalan(aktif: boolean): number {
  const [detik, setDetik] = useState(0);
  useEffect(() => {
    if (!aktif) return;
    const mulai = Date.now();
    const timer = setInterval(() => setDetik(Math.floor((Date.now() - mulai) / 1000)), 1000);
    return () => {
      clearInterval(timer);
      setDetik(0);
    };
  }, [aktif]);
  return detik;
}

/** Peringatan browser bila tab ditutup / dimuat ulang saat proses masih berjalan. */
export function useCegahTutupTab(aktif: boolean) {
  useEffect(() => {
    if (!aktif) return;
    const handler = (event: BeforeUnloadEvent) => event.preventDefault();
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, [aktif]);
}
