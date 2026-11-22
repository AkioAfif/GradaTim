"use client";

import { useEffect, useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import AuthShell, { inputClass, labelClass, primaryButtonClass } from "../../components/AuthShell";
import { useAuth } from "../../context/AuthContext";
import { ApiError } from "../../lib/api/client";
import { pesanError } from "../../lib/api/queries";

// Batas sama dengan backend (schemas/user.py): bcrypt mengabaikan byte setelah ke-72.
const PASSWORD_MIN = 8;
const PASSWORD_MAKS_BYTE = 72;

function validasiPassword(password: string): string {
  if (password.length < PASSWORD_MIN) return `Password minimal ${PASSWORD_MIN} karakter`;
  if (new TextEncoder().encode(password).length > PASSWORD_MAKS_BYTE) {
    return `Password maksimal ${PASSWORD_MAKS_BYTE} byte`;
  }
  return "";
}

export default function RegisterPage() {
  const router = useRouter();
  const { status, register } = useAuth();

  const [nama, setNama] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (status === "authenticated") router.replace("/");
  }, [status, router]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setFieldErrors({});

    const errorPassword = validasiPassword(password);
    if (errorPassword) {
      setFieldErrors({ password: errorPassword });
      return;
    }

    setSubmitting(true);
    try {
      await register({ nama: nama.trim(), email: email.trim(), password });
    } catch (err) {
      if (err instanceof ApiError && Object.keys(err.fieldErrors).length > 0) {
        setFieldErrors(err.fieldErrors);
      } else {
        setError(pesanError(err)); // mis. 409 "Email sudah terdaftar"
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AuthShell
      title="Buat Akun"
      subtitle="Mulai pecah targetmu jadi langkah kecil yang terjadwal."
      footer={
        <>
          Sudah punya akun?{" "}
          <Link href="/login" className="font-medium text-[#506851] hover:underline">
            Masuk
          </Link>
        </>
      }
    >
      <form onSubmit={handleSubmit} className="space-y-5" noValidate>
        <div>
          <label htmlFor="nama" className={labelClass}>
            Nama
          </label>
          <input
            id="nama"
            autoComplete="name"
            required
            maxLength={100}
            value={nama}
            onChange={(event) => setNama(event.target.value)}
            className={inputClass}
          />
          {fieldErrors.nama && <p className="mt-1 text-xs text-[#8A3B2E]">{fieldErrors.nama}</p>}
        </div>

        <div>
          <label htmlFor="email" className={labelClass}>
            Email
          </label>
          <input
            id="email"
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            className={inputClass}
          />
          {fieldErrors.email && <p className="mt-1 text-xs text-[#8A3B2E]">{fieldErrors.email}</p>}
        </div>

        <div>
          <label htmlFor="password" className={labelClass}>
            Password
          </label>
          <input
            id="password"
            type="password"
            autoComplete="new-password"
            required
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            className={inputClass}
          />
          <p className={`mt-1 text-xs ${fieldErrors.password ? "text-[#8A3B2E]" : "text-[#8B857B]"}`}>
            {fieldErrors.password || `Minimal ${PASSWORD_MIN} karakter.`}
          </p>
        </div>

        {error && (
          <p role="alert" className="rounded-lg bg-[#F8E1DA] px-4 py-3 text-sm text-[#8A3B2E]">
            {error}
          </p>
        )}

        <button
          type="submit"
          disabled={submitting || !nama.trim() || !email || !password}
          className={primaryButtonClass}
        >
          {submitting ? "Memproses..." : "Daftar"}
        </button>
      </form>
    </AuthShell>
  );
}
