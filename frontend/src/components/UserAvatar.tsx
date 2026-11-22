"use client";

import { useAuth } from "../context/AuthContext";

/** Lingkaran inisial nama user di header halaman. */
export default function UserAvatar() {
  const { user } = useAuth();
  const inisial = user?.nama.trim().charAt(0).toUpperCase() || "?";

  return (
    <div
      title={user ? `${user.nama} (${user.email})` : undefined}
      className="flex h-9 w-9 items-center justify-center rounded-full bg-[#D7B99B] text-sm font-medium text-white"
    >
      {inisial}
    </div>
  );
}
