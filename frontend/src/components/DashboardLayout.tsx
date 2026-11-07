
"use client";

import type { ReactNode } from "react";
import Sidebar from "./Sidebar";

type DashboardLayoutProps = {
  children: ReactNode;
};

export default function DashboardLayout({
  children,
}: DashboardLayoutProps) {
  return (
    <div className="flex min-h-screen bg-[#FAF6EE] text-[#30312B]">
      <Sidebar />

      <main className="min-w-0 flex-1 px-8 py-7 lg:px-12">
        {children}
      </main>
    </div>
  );
}
