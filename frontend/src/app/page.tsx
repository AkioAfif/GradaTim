
"use client";

import Button from "../components/Button";

export default function Home() {
  return (
    <main className="min-h-screen flex flex-col items-center justify-center bg-gray-50">
      <h1 className="text-4xl font-bold text-gray-800">
        GradaTim
      </h1>

      <p className="mt-4 text-gray-600">
        AI Personal Manager
      </p>

      <p className="mt-2 text-sm text-gray-500">
        Frontend Development - Initial Setup
      </p>

      <div className="mt-6">
        <Button
          label="Mulai Sekarang"
          onClick={() => alert("Selamat datang di GradaTim!")}
        />
      </div>
    </main>
  );
}
