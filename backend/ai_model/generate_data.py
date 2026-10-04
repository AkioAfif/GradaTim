"""
generate_data.py — GradaTim Mood Capacity Dataset Generator

Tujuan:
    Membuat dataset sintetis yang merepresentasikan hubungan antara
    jawaban kuesioner mood pengguna dengan kapasitas kerja mereka hari itu.
"""

import numpy as np
import pandas as pd

np.random.seed(42)

N_SAMPLES = 1000


def generate_mood_dataset(n: int = N_SAMPLES) -> pd.DataFrame:
    """
    Generate synthetic mood questionnaire dataset.

    5 Pertanyaan Kuesioner (skor 1-5 per pertanyaan):
        Q1: Seberapa fokus kamu hari ini?           (1=sangat tidak fokus, 5=sangat fokus)
        Q2: Seberapa tenang perasaanmu?             (1=sangat cemas, 5=sangat tenang)
        Q3: Seberapa termotivasi kamu?              (1=tidak sama sekali, 5=sangat termotivasi)
        Q4: Seberapa cukup tidurmu semalam?         (1=sangat kurang, 5=sangat cukup)
        Q5: Seberapa siap kamu menghadapi tugas?    (1=tidak siap, 5=sangat siap)

    Label (Target Output):
        0 = LOW    → Rekomendasikan maks 2 task, pilih yang ringan & high impact
        1 = MEDIUM → Rekomendasikan 3-4 task, urutan normal berdasarkan prioritas
        2 = HIGH   → Rekomendasikan 5-6 task, bisa dorong task berat sekalian
    """

    # --- GENERATE RAW MOOD SCORES ---
    questions = np.random.randint(1, 6, size=(n, 5))  # shape: (1000, 5)
    q1, q2, q3, q4, q5 = questions[:, 0], questions[:, 1], questions[:, 2], questions[:, 3], questions[:, 4]

    # --- HITUNG TOTAL SKOR (range: 5 sampai 25) ---
    total_score = q1 + q2 + q3 + q4 + q5

    labels = np.where(total_score <= 13, 0,
              np.where(total_score <= 18, 1, 2))

    # --- TAMBAHKAN NOISE (~15%) ---
    noise_mask = np.random.random(n) < 0.15  # 15% data akan di-flip labelnya
    noise_amount = np.random.choice([-1, 1], size=n)
    labels_noisy = np.clip(labels + noise_mask * noise_amount, 0, 2).astype(int)

    df = pd.DataFrame({
        'q1_focus':      q1,
        'q2_calm':       q2,
        'q3_motivated':  q3,
        'q4_sleep':      q4,
        'q5_readiness':  q5,
        'total_score':   total_score,
        'capacity_level': labels_noisy
    })

    return df


if __name__ == "__main__":
    df = generate_mood_dataset()

    df.to_csv("mood_dataset.csv", index=False)
    print(f"Dataset berhasil dibuat: {len(df)} baris")
    print(f"\nDistribusi label:")
    print(df['capacity_level'].value_counts().sort_index())
    print(f"\n5 baris pertama:")
    print(df.head())
