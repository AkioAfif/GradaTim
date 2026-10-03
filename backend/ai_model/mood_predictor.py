"""
mood_predictor.py — GradaTim Mood Model Inference Module

Tujuan:
    Module ini dipakai oleh backend (ai_service.py) untuk:
    1. Load model terlatih dari file .pkl
    2. Menerima jawaban kuesioner dari pengguna
    3. Memprediksi kapasitas kerja mereka
    4. Mengembalikan rekomendasi task yang sesuai
"""

import joblib
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional

MODEL_PATH = Path(__file__).parent / "mood_model.pkl"

_model = None

def _get_model():
    """Lazy load model — hanya load sekali, simpan di memory."""
    global _model
    if _model is None:
        if not MODEL_PATH.exists():
            raise FileNotFoundError(
                f"Model belum ditraining! Jalankan dulu: python train_model.py\n"
                f"Expected path: {MODEL_PATH}"
            )
        _model = joblib.load(MODEL_PATH)
    return _model


def predict_capacity(mood_answers: List[int]) -> Dict[str, Any]:
    """
    Prediksi kapasitas kerja pengguna berdasarkan jawaban kuesioner mood.

    Args:
        mood_answers: List 5 integer, masing-masing bernilai 1-5.
                      Urutan: [fokus, tenang, motivasi, tidur, siap]

    Returns:
        dict berisi:
            - capacity_level: "LOW", "MEDIUM", atau "HIGH"
            - capacity_index: 0, 1, atau 2 (index numerik)
            - confidence: float (0-1), seberapa yakin model
            - probabilities: dict probabilitas per kelas
            - max_tasks: int, jumlah task maksimal yang direkomendasikan
            - recommendation_message: string pesan untuk ditampilkan ke user

    Raises:
        ValueError: Jika input tidak valid

    Example:
        >>> result = predict_capacity([4, 3, 5, 4, 4])
        >>> print(result['capacity_level'])
        'HIGH'
        >>> print(result['max_tasks'])
        5
    """
    if len(mood_answers) != 5:
        raise ValueError(f"Harus ada 5 jawaban, diterima {len(mood_answers)}")
    if not all(1 <= ans <= 5 for ans in mood_answers):
        raise ValueError("Setiap jawaban harus antara 1 dan 5")

    total_score = sum(mood_answers)
    features = np.array(mood_answers + [total_score]).reshape(1, -1)    # Shape: (1, 6) — 5 jawaban + total skor

    model = _get_model()
    capacity_index = int(model.predict(features)[0])
    probabilities = model.predict_proba(features)[0]

    # --- MAP KE LABEL & REKOMENDASI ---
    CAPACITY_CONFIG = {
        0: {
            "level": "LOW",
            "max_tasks": 2,
            "message": "Kondisimu hari ini kurang prima. Fokus ke 2 tugas terpenting yang paling ringan. Istirahat juga perlu!"
        },
        1: {
            "level": "MEDIUM",
            "max_tasks": 4,
            "message": "Kondisimu hari ini cukup baik. Kamu bisa menyelesaikan 3-4 tugas dengan nyaman."
        },
        2: {
            "level": "HIGH",
            "max_tasks": 6,
            "message": "Kamu dalam kondisi prima hari ini! Manfaatkan energimu untuk menyelesaikan tugas-tugas yang lebih menantang."
        }
    }

    config = CAPACITY_CONFIG[capacity_index]

    return {
        "capacity_level": config["level"],
        "capacity_index": capacity_index,
        "confidence": round(float(probabilities[capacity_index]), 4),
        "probabilities": {
            "LOW":    round(float(probabilities[0]), 4),
            "MEDIUM": round(float(probabilities[1]), 4),
            "HIGH":   round(float(probabilities[2]), 4),
        },
        "max_tasks": config["max_tasks"],
        "total_mood_score": total_score,
        "recommendation_message": config["message"]
    }


URGENCY_WEIGHT = 2.0


def urgency_score(day_number: Optional[int], today_day: int) -> int:
    """
    Seberapa mendesak task, berdasarkan sisa hari menuju jadwalnya.
        0 = tidak diketahui / masih jauh (>= 7 hari lagi)
        1 = 3-6 hari lagi · 2 = 1-2 hari lagi · 3 = jadwalnya hari ini atau sudah lewat
    """
    if day_number is None:
        return 0
    days_left = day_number - today_day
    if days_left <= 0:
        return 3
    if days_left <= 2:
        return 2
    if days_left <= 6:
        return 1
    return 0


def filter_tasks_by_capacity(
    tasks: List[Dict],
    capacity_level: str,
    max_tasks: int,
    today_day: int = 1,
) -> List[Dict]:
    """
    Pilih dan urutkan task hari ini sesuai kapasitas mood, urgensi, dan dependensi.

    Args:
        tasks: List task. Field yang dipakai (semuanya opsional):
            effort_level / impact_level: "low" | "medium" | "high" (default "medium")
            day_number: hari jadwal task (untuk urgensi)
            task_number + depends_on: prasyarat antar task
            status: "done" → dianggap sudah selesai, tidak direkomendasikan lagi
        capacity_level: "LOW", "MEDIUM", atau "HIGH"
        max_tasks: Jumlah maksimal task yang direkomendasikan
        today_day: Hari ke berapa sekarang (hari ke-1 = hari goal dibuat)

    Returns:
        List task terpilih, urut prioritas. Task selalu muncul SETELAH prasyaratnya,
        dan hanya dipilih jika semua prasyaratnya sudah selesai atau ikut terpilih hari ini.
    """
    EFFORT_SCORE = {"low": 1, "medium": 2, "high": 3}
    IMPACT_SCORE = {"low": 1, "medium": 2, "high": 3}

    def mood_fit(task: Dict) -> float:
        effort = EFFORT_SCORE.get(task.get("effort_level", "medium"), 2)
        impact = IMPACT_SCORE.get(task.get("impact_level", "medium"), 2)

        if capacity_level == "LOW":
            # Prioritaskan impact tinggi, effort rendah
            return (impact * 3) - (effort * 2)
        elif capacity_level == "MEDIUM":
            # Seimbang: sedikit lebih ke impact
            return impact * 1.5 - effort * 0.5
        else:
            # HIGH: dorong yang menantang
            return impact + effort

    def score_task(task: Dict) -> float:
        return mood_fit(task) + URGENCY_WEIGHT * urgency_score(task.get("day_number"), today_day)

    done = {t.get("task_number") for t in tasks if t.get("status") == "done"}
    remaining = [t for t in tasks if t.get("status") != "done"]
    selected: List[Dict] = []
    unlocked_by = done.copy()  # task_number yang sudah selesai / sudah terpilih hari ini

    # Greedy: tiap putaran ambil task skor tertinggi yang semua prasyaratnya sudah terpenuhi
    while remaining and len(selected) < max_tasks:
        eligible = [t for t in remaining if all(d in unlocked_by for d in t.get("depends_on", []))]
        if not eligible:
            break
        best = max(eligible, key=lambda t: (score_task(t), -(t.get("day_number") or 0)))
        selected.append(best)
        remaining.remove(best)
        unlocked_by.add(best.get("task_number"))

    return selected
