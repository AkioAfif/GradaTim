
"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  House,
  ListTodo,
  CalendarDays,
  ChartNoAxesColumn,
  Settings,
  LogOut,
} from "lucide-react";

const menuItems = [
  { label: "Beranda", href: "/", icon: House },
  { label: "Tugas", href: "/tasks", icon: ListTodo },
  { label: "Kalender", href: "/calendar", icon: CalendarDays },
  { label: "Analitik", href: "/analytics", icon: ChartNoAxesColumn },
  { label: "Pengaturan", href: "/settings", icon: Settings },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="flex w-44 shrink-0 flex-col border-r border-[#E9E0D4] bg-[#F4F0E7] px-4 py-6 md:min-h-screen">
      <Link
        href="/"
        className="mb-10 flex items-center gap-1 text-xl font-bold tracking-tight text-[#506851]"
      >
        <span className="text-2xl">✦</span>
        GradaTim
      </Link>

      <nav className="flex flex-col gap-2">
        {menuItems.map((item) => {
          const Icon = item.icon;
          const active = pathname === item.href;

          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 rounded-lg px-3 py-3 text-xs transition ${
                active
                  ? "bg-[#506851] font-medium text-white"
                  : "text-[#64675E] hover:bg-[#EAE7DD]"
              }`}
            >
              <Icon size={15} />
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="mt-auto pt-10">
        <button
          type="button"
          disabled
          title="Logout tersedia setelah integrasi autentikasi"
          className="flex w-full cursor-not-allowed items-center gap-2 rounded-lg bg-[#E5E8DC] px-3 py-2.5 text-xs text-[#506851] opacity-75"
        >
          <LogOut size={15} />
          Keluar
        </button>
      </div>
    </aside>
  );
}
