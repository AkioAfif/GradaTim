"use client";

import { useSyncExternalStore } from "react";

// Wizard planning: semua data ada di server; browser hanya mengingat goal mana yang sedang
// direncanakan (id_goal) selama tab terbuka, supaya Kembali ke langkah 1 mengedit goal yang sama
// (PATCH), bukan membuat goal ganda.

const KEY = "gradatim-planning-goal";
const listeners = new Set<() => void>();

function baca(): number | null {
  try {
    const nilai = Number(sessionStorage.getItem(KEY));
    return Number.isInteger(nilai) && nilai > 0 ? nilai : null;
  } catch {
    return null;
  }
}

function beritahu() {
  listeners.forEach((listener) => listener());
}

export function setIdGoalWizard(idGoal: number): void {
  try {
    sessionStorage.setItem(KEY, String(idGoal));
  } catch {
    // tanpa sessionStorage wizard tetap jalan di tab ini lewat state halaman
  }
  beritahu();
}

export function clearIdGoalWizard(): void {
  try {
    sessionStorage.removeItem(KEY);
  } catch {
    // abaikan
  }
  beritahu();
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

/**
 * id_goal yang sedang direncanakan.
 * - `undefined` saat render di server / sebelum hidrasi (belum diketahui)
 * - `null` bila belum ada goal di wizard
 */
export function useIdGoalWizard(): number | null | undefined {
  return useSyncExternalStore(subscribe, baca, () => undefined);
}
