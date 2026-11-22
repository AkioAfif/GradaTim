"use client";

import { useState, type ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { ApiError } from "../lib/api/client";
import { AuthProvider } from "../context/AuthContext";
// Sementara: halaman yang belum tersambung ke API masih memakai data lokal ini.
import { TaskProvider } from "../context/TaskContext";

function buatQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 30_000,
        refetchOnWindowFocus: true,
        // Error 4xx (404, 409, 422) tidak akan berubah bila diulang; hanya ulangi error jaringan/5xx.
        retry: (failureCount, error) => {
          if (error instanceof ApiError && error.status >= 400 && error.status < 500) return false;
          return failureCount < 2;
        },
      },
      mutations: {
        retry: false,
      },
    },
  });
}

export default function Providers({ children }: { children: ReactNode }) {
  // Satu QueryClient per tab browser (useState agar tidak dibuat ulang tiap render).
  const [queryClient] = useState(buatQueryClient);

  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <TaskProvider>{children}</TaskProvider>
      </AuthProvider>
    </QueryClientProvider>
  );
}
