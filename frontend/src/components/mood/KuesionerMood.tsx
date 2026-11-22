"use client";

import { useState, type FormEvent } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import { errorBoxClass, primaryButtonClass, secondaryButtonClass } from "../ui";
import { toApiError, type ApiError } from "../../lib/api/client";
import { isiMood } from "../../lib/api/mood";
import { queryKeys } from "../../lib/api/queries";
import type { MoodAnswers, MoodHariIni } from "../../lib/api/types";
import { PERTANYAAN_MOOD, jawabanLengkap, type JawabanSebagian } from "../../lib/mood";

/** Kuesioner mood 5 pertanyaan (skala 1–5) → POST /mood. Mengisi ulang di hari yang sama menimpa hasil lama. */
export default function KuesionerMood({
  awal,
  onBatal,
  onTersimpan,
}: {
  awal?: MoodAnswers;
  onBatal?: () => void;
  onTersimpan?: () => void;
}) {
  const queryClient = useQueryClient();
  const [jawaban, setJawaban] = useState<JawabanSebagian>(awal ?? {});
  const [errorForm, setErrorForm] = useState("");

  const kirim = useMutation<MoodHariIni, ApiError, MoodAnswers>({
    mutationFn: async (data) => {
      try {
        return await isiMood(data);
      } catch (err) {
        throw toApiError(err);
      }
    },
    onSuccess: (hasil) => {
      queryClient.setQueryData(queryKeys.moodHariIni, hasil);
      onTersimpan?.();
    },
  });

  const terjawab = PERTANYAAN_MOOD.filter((p) => jawaban[p.kunci] !== undefined).length;

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setErrorForm("");
    const lengkap = jawabanLengkap(jawaban);
    if (!lengkap) {
      setErrorForm("Jawab semua pertanyaan terlebih dahulu.");
      return;
    }
    kirim.mutate(lengkap);
  }

  return (
    <form onSubmit={handleSubmit} noValidate className="space-y-4">
      {PERTANYAAN_MOOD.map((p, indeks) => (
        <fieldset key={p.kunci} className="rounded-xl border border-[#E7DBCC] bg-[#FFFCF7] p-5">
          <legend className="sr-only">{p.teks}</legend>
          <p aria-hidden className="text-sm font-semibold">
            {indeks + 1}. {p.teks}
          </p>
          <div className="mt-4 grid grid-cols-5 gap-2">
            {[1, 2, 3, 4, 5].map((nilai) => {
              const dipilih = jawaban[p.kunci] === nilai;
              return (
                <label
                  key={nilai}
                  className={`flex cursor-pointer items-center justify-center rounded-lg border py-3 text-sm font-medium transition has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-[#82947B] ${
                    dipilih
                      ? "border-[#506851] bg-[#506851] text-white"
                      : "border-[#E5D9C9] bg-white text-[#57564F] hover:bg-[#F3EADD]"
                  }`}
                >
                  <input
                    type="radio"
                    name={p.kunci}
                    value={nilai}
                    checked={dipilih}
                    disabled={kirim.isPending}
                    onChange={() => setJawaban((sebelum) => ({ ...sebelum, [p.kunci]: nilai }))}
                    aria-label={`${nilai}${nilai === 1 ? ` (${p.rendah})` : nilai === 5 ? ` (${p.tinggi})` : ""}`}
                    className="sr-only"
                  />
                  {nilai}
                </label>
              );
            })}
          </div>
          <div className="mt-2 flex justify-between text-xs text-[#8B857B]">
            <span>{p.rendah}</span>
            <span>{p.tinggi}</span>
          </div>
        </fieldset>
      ))}

      {errorForm && <p className={errorBoxClass}>{errorForm}</p>}
      {kirim.isError && (
        <p role="alert" className={errorBoxClass}>
          {kirim.error.status === 503
            ? "Layanan penilaian mood sedang tidak tersedia. Coba lagi beberapa saat lagi."
            : kirim.error.message}
        </p>
      )}

      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-[#8B857B]">{terjawab} dari {PERTANYAAN_MOOD.length} terjawab</p>
        <div className="flex gap-3">
          {onBatal && (
            <button type="button" onClick={onBatal} disabled={kirim.isPending} className={secondaryButtonClass}>
              Batal
            </button>
          )}
          <button type="submit" disabled={kirim.isPending} className={primaryButtonClass}>
            {kirim.isPending ? "Menilai..." : "Lihat rekomendasi"}
          </button>
        </div>
      </div>
    </form>
  );
}
