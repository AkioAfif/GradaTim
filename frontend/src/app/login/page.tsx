"use client";

import { Suspense, useEffect, useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";

import AuthShell, {
  inputClass,
  labelClass,
  primaryButtonClass,
  tujuanAman,
} from "../../components/AuthShell";
import { useAuth } from "../../context/AuthContext";
import { pesanError } from "../../lib/api/queries";

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const tujuan = tujuanAman(searchParams.get("next"));
  const { status, login } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (status === "authenticated") router.replace(tujuan);
  }, [status, router, tujuan]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      await login({ email: email.trim(), password });
      // redirect dilakukan efek di atas begitu status = authenticated
    } catch (err) {
      setError(pesanError(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5" noValidate>
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
      </div>

      <div>
        <label htmlFor="password" className={labelClass}>
          Password
        </label>
        <input
          id="password"
          type="password"
          autoComplete="current-password"
          required
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          className={inputClass}
        />
      </div>

      {error && (
        <p role="alert" className="rounded-lg bg-[#F8E1DA] px-4 py-3 text-sm text-[#8A3B2E]">
          {error}
        </p>
      )}

      <button type="submit" disabled={submitting || !email || !password} className={primaryButtonClass}>
        {submitting ? "Memproses..." : "Masuk"}
      </button>
    </form>
  );
}

export default function LoginPage() {
  return (
    <AuthShell
      title="Masuk"
      subtitle="Lanjutkan rencanamu, satu langkah kecil setiap hari."
      footer={
        <>
          Belum punya akun?{" "}
          <Link href="/register" className="font-medium text-[#506851] hover:underline">
            Daftar
          </Link>
        </>
      }
    >
      {/* useSearchParams butuh batas Suspense agar halaman tetap bisa di-prerender (Next 16). */}
      <Suspense fallback={<p className="text-sm text-[#8B857B]">Memuat...</p>}>
        <LoginForm />
      </Suspense>
    </AuthShell>
  );
}
