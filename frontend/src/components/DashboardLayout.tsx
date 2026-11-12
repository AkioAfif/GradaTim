
"use client";

import type { ReactNode } from "react";
import Sidebar from "./Sidebar";

export default function DashboardLayout({
  children,
}: {
  children: ReactNode;
}) {
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
