
"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  House,
  ListTodo,
  CalendarDays,
  ChartNoAxesColumn,
  Settings,
  Leaf,
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
    <aside className="flex min-h-screen w-64 flex-col border-r border-[#E8DED1] bg-[#F6F0E6] px-5 py-7">
      <div className="mb-12 flex items-center gap-2">
        <Leaf className="text-[#64765C]" size={25} />
        <h1 className="text-2xl font-bold text-[#2F3029]">
          GradaTim
        </h1>
      </div>

      <nav className="flex flex-col gap-2">
        {menuItems.map((item) => {
          const Icon = item.icon;
          const active = pathname === item.href;

          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 rounded-xl px-4 py-3 text-sm font-medium transition ${
                active
                  ? "bg-[#64765C] text-white"
                  : "text-[#4D5148] hover:bg-[#E8E4D8]"
              }`}
            >
              <Icon size={19} />
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="mt-auto pt-10">
        <button
          type="button"
          className="flex w-full items-center gap-3 rounded-xl bg-[#826049] px-4 py-3 text-sm text-white"
        >
          <LogOut size={18} />
          Keluar
        </button>
      </div>
    </aside>
  );
}
