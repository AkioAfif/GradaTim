import type { ReactNode } from "react";

/** Kerangka halaman login/register (tanpa sidebar), memakai palet dashboard. */
export default function AuthShell({
  title,
  subtitle,
  children,
  footer,
}: {
  title: string;
  subtitle: string;
  children: ReactNode;
  footer: ReactNode;
}) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-[#E9E6DF] p-4 text-[#30312B]">
      <div className="w-full max-w-md rounded-2xl bg-[#FFFAF3] p-6 shadow-sm sm:p-8">
        <p className="flex items-center gap-1 text-xl font-bold tracking-tight text-[#506851]">
          <span className="text-2xl">✦</span>
          GradaTim
        </p>

        <h1 className="mt-6 text-2xl font-medium">{title}</h1>
        <p className="mt-2 text-sm text-[#8B857B]">{subtitle}</p>

        <div className="mt-6">{children}</div>

        <p className="mt-6 text-center text-sm text-[#8B857B]">{footer}</p>
      </div>
    </div>
  );
}

export const inputClass =
  "w-full rounded-lg border border-[#E5D9C9] bg-white px-4 py-3 text-sm outline-none focus:border-[#64765C]";

export const labelClass = "mb-2 block text-sm font-semibold";

export const primaryButtonClass =
  "w-full rounded-lg bg-[#826049] px-6 py-3 text-sm font-medium text-white hover:bg-[#6D4D38] disabled:cursor-not-allowed disabled:opacity-60";

/** Tujuan redirect setelah login: hanya path internal (cegah open redirect / `javascript:`). */
export function tujuanAman(next: string | null): string {
  if (!next || !next.startsWith("/") || next.startsWith("//") || next.startsWith("/\\")) {
    return "/";
  }
  if (next.startsWith("/login") || next.startsWith("/register")) return "/";
  return next;
}
