
"use client";

import { useEffect, type ReactNode } from "react";
import { usePathname, useRouter } from "next/navigation";

import Sidebar from "./Sidebar";
import { useAuth } from "../context/AuthContext";

/** Layout halaman dashboard. Sekaligus guard auth: tanpa login → /login?next=<halaman ini>. */
export default function DashboardLayout({
  children,
}: {
  children: ReactNode;
}) {
  const { status, errorMessage, keluarManual, retry, logout } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (status === "unauthenticated") {
      // Habis menekan Keluar: jangan simpan halaman terakhir untuk user berikutnya.
      router.replace(keluarManual ? "/login" : `/login?next=${encodeURIComponent(pathname)}`);
    }
  }, [status, keluarManual, router, pathname]);

  if (status !== "authenticated") {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#E9E6DF] p-4 text-[#30312B]">
        {status === "error" ? (
          <div className="max-w-sm rounded-2xl bg-[#FFFAF3] p-6 text-center shadow-sm">
            <p className="font-medium">Tidak bisa memuat akunmu</p>
            <p className="mt-2 text-sm text-[#8B857B]">{errorMessage}</p>
            <div className="mt-5 flex justify-center gap-3">
              <button
                type="button"
                onClick={retry}
                className="rounded-lg bg-[#826049] px-5 py-2.5 text-sm font-medium text-white hover:bg-[#6D4D38]"
              >
                Coba lagi
              </button>
              <button
                type="button"
                onClick={logout}
                className="rounded-lg border border-[#DDD2C3] bg-[#ECE9E1] px-5 py-2.5 text-sm font-medium"
              >
                Keluar
              </button>
            </div>
          </div>
        ) : (
          <p className="text-sm text-[#8B857B]">Memuat...</p>
        )}
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#E9E6DF] p-2 text-[#30312B] sm:p-3">
      <div className="mx-auto flex min-h-[calc(100vh-24px)] max-w-[1440px] overflow-hidden rounded-2xl bg-[#FFFAF3] shadow-sm">
        <Sidebar />

        <main className="min-w-0 flex-1 px-5 py-6 md:px-9 lg:px-12">
          {children}
        </main>
      </div>
    </div>
  );
}
