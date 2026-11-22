"use client";

import { useEffect, useId, type ReactNode } from "react";
import { X } from "lucide-react";

/** Dialog modal sederhana: klik latar / Esc menutup (kecuali `kunci` saat proses berjalan). */
export default function Modal({
  judul,
  onTutup,
  kunci = false,
  children,
}: {
  judul: string;
  onTutup: () => void;
  kunci?: boolean;
  children: ReactNode;
}) {
  const idJudul = useId();

  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      if (event.key === "Escape" && !kunci) onTutup();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onTutup, kunci]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      onClick={() => !kunci && onTutup()}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby={idJudul}
        onClick={(event) => event.stopPropagation()}
        className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-2xl bg-[#FFFAF3] p-6 text-[#30312B] shadow-xl"
      >
        <div className="flex items-start justify-between gap-4">
          <h2 id={idJudul} className="text-lg font-semibold">
            {judul}
          </h2>
          <button
            type="button"
            onClick={onTutup}
            disabled={kunci}
            aria-label="Tutup"
            className="rounded-md p-1 text-[#8B857B] hover:bg-[#ECE9E1] disabled:opacity-40"
          >
            <X size={20} />
          </button>
        </div>
        <div className="mt-5">{children}</div>
      </div>
    </div>
  );
}
