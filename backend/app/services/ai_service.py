"""LLM integration & prompting logic

Dua fitur AI GradaTim:
    1. Goal Decomposition (FR-2) — memecah goal jadi milestone & task harian via LLM
       (default Gemini, lewat OpenAI-compatible API + structured output JSON schema),
       lalu dinormalisasi supaya aman dipakai scheduler.
    2. Mood Capacity (FR-6 & FR-7) — wrapper untuk model RandomForest di ai_model/.
"""

from datetime import date
from typing import Any, Optional

from openai import OpenAI, OpenAIError
from pydantic import ValidationError

from ai_model.mood_predictor import filter_tasks_by_capacity, predict_capacity
from app.core.config import settings
from app.schemas.ai_decomposition import GoalDecomposition, GoalDecompositionRequest
from app.schemas.mood import MoodAnswers, MoodAssessment

MIN_TASK_MINUTES = 10
MAX_TASK_MINUTES = 240


class AIServiceError(Exception):
    """Error yang aman ditampilkan ke user (endpoint bisa map ke HTTP 502/503)."""


# ============================================================
# GOAL DECOMPOSITION (FR-2)
# ============================================================

SYSTEM_PROMPT = """Kamu adalah perencana target pribadi untuk aplikasi GradaTim.
Tugasmu memecah satu goal besar menjadi milestone berurutan, lalu setiap milestone menjadi task harian yang konkret.

Aturan:
- Tulis semua judul dalam Bahasa Indonesia, singkat, dan diawali kata kerja (contoh: "Install Docker Desktop & verifikasi CLI").
- Setiap task harus bisa langsung dikerjakan tanpa perlu dipecah lagi, dan hasilnya jelas terlihat.
- Buat 2-6 milestone. Setiap milestone berisi 2-8 task.
- day_number dimulai dari 1 dan tidak boleh melebihi jumlah hari yang tersedia.
- Sebar task secara merata; jangan menumpuk banyak task berat di hari yang sama.
- Sisakan hari-hari terakhir sebagai buffer bila waktunya longgar.
- estimated_minutes realistis, antara 10 dan 240 menit per task.
- effort_level: seberapa berat usaha/energi mental task tersebut (low/medium/high).
- impact_level: seberapa besar kontribusi task terhadap tercapainya goal (low/medium/high).
- task_number: nomor unik 1, 2, 3, ... berurutan di seluruh goal (bukan per milestone).
- depends_on: daftar task_number yang WAJIB selesai sebelum task ini bisa dikerjakan
  (contoh: "Jalankan container" bergantung pada "Install Docker"). Hanya boleh menunjuk task
  dengan day_number lebih awal atau sama. Kosongkan ([]) jika tidak ada prasyarat.
- Jangan membuat pengguna kewalahan: lebih baik task kecil yang konsisten daripada task besar yang menakutkan."""


def _build_user_prompt(request: GoalDecompositionRequest, today: date, total_days: int) -> str:
    lines = [
        f"Goal: {request.judul_goal}",
        f"Deskripsi: {request.deskripsi or '-'}",
        f"Tanggal hari ini: {today.isoformat()}",
        f"Deadline: {request.deadline.isoformat()} ({total_days} hari tersedia, hari ke-1 = hari ini)",
    ]
    if request.menit_harian:
        lines.append(
            f"Waktu luang pengguna: maksimal {request.menit_harian} menit per hari. "
            "Total estimated_minutes di hari yang sama tidak boleh melebihi batas ini."
        )
    return "\n".join(lines)


def _normalize(result: GoalDecomposition, total_days: int) -> GoalDecomposition:
    """Jangan percaya output LLM mentah: rapikan urutan & clamp angka ke rentang valid."""
    milestones = [m for m in result.milestones if m.tasks]
    if not milestones:
        raise AIServiceError("AI tidak menghasilkan task apa pun. Coba perjelas deskripsi goal-mu.")

    milestones.sort(key=lambda m: m.order)
    for index, milestone in enumerate(milestones, start=1):
        milestone.order = index
        for task in milestone.tasks:
            task.day_number = min(max(task.day_number, 1), total_days)
            task.estimated_minutes = min(max(task.estimated_minutes, MIN_TASK_MINUTES), MAX_TASK_MINUTES)
        milestone.tasks.sort(key=lambda t: t.day_number)

    result.milestones = milestones
    _normalize_dependencies([t for m in milestones for t in m.tasks])
    result.estimated_total_days = max(t.day_number for m in milestones for t in m.tasks)
    return result


def _normalize_dependencies(tasks: list) -> None:
    """
    Nomori ulang task 1..N sesuai urutan akhir, lalu bersihkan depends_on:
    buang referensi ke task yang tidak ada / diri sendiri / task yang lebih belakang
    (aturan terakhir sekaligus mencegah dependensi melingkar).
    """
    old_numbers = [t.task_number for t in tasks]
    numbers_unique = len(set(old_numbers)) == len(old_numbers)
    renumber = {old: new for new, old in enumerate(old_numbers, start=1)} if numbers_unique else {}

    for new_number, task in enumerate(tasks, start=1):
        task.task_number = new_number
        # nomor dari LLM duplikat → tidak bisa dipetakan dengan aman, dependensi dibuang
        mapped = {renumber[d] for d in task.depends_on if d in renumber}
        task.depends_on = sorted(d for d in mapped if d < new_number and tasks[d - 1].day_number <= task.day_number)


def _get_client() -> OpenAI:
    if not settings.LLM_API_KEY:
        raise AIServiceError("LLM_API_KEY belum diset di .env")
    # max_retries: 429/503 (kuota / server Gemini penuh) sering hanya sesaat, SDK retry dengan backoff
    return OpenAI(api_key=settings.LLM_API_KEY, base_url=settings.LLM_BASE_URL, timeout=90, max_retries=4)


def decompose_goal(
    request: GoalDecompositionRequest,
    today: Optional[date] = None,
    client: Optional[OpenAI] = None,
) -> GoalDecomposition:
    """
    Pecah goal user menjadi milestone & task harian (kontrak JSON di spesifikasi bagian 5A).

    Args:
        request: judul, deskripsi, deadline, dan (opsional) menit luang per hari
        today: override tanggal hari ini (untuk testing)
        client: override LLM client (untuk testing)

    Raises:
        AIServiceError: deadline sudah lewat, API gagal, atau output AI tidak bisa dipakai
    """
    today = today or date.today()
    total_days = (request.deadline - today).days + 1  # inklusif: deadline hari ini = 1 hari
    if total_days < 1:
        raise AIServiceError("Deadline sudah lewat. Pilih tanggal hari ini atau setelahnya.")

    client = client or _get_client()
    try:
        completion = client.chat.completions.parse(
            model=settings.LLM_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": _build_user_prompt(request, today, total_days)},
            ],
            response_format=GoalDecomposition,
        )
    except OpenAIError as e:  # termasuk kuota habis (429), key salah, output terpotong
        raise AIServiceError("Layanan AI sedang tidak tersedia. Coba lagi sebentar lagi.") from e
    except ValidationError as e:  # JSON dari LLM tidak sesuai schema
        raise AIServiceError("Format jawaban AI tidak valid. Coba lagi.") from e

    result = completion.choices[0].message.parsed
    if result is None:  # model menolak (refusal)
        raise AIServiceError("AI tidak bisa memproses goal ini. Coba ubah judul atau deskripsinya.")

    return _normalize(result, total_days)


# ============================================================
# MOOD CAPACITY (FR-6 & FR-7)
# ============================================================

def assess_mood(answers: MoodAnswers) -> MoodAssessment:
    """Prediksi kapasitas kerja hari ini dari 5 jawaban kuesioner."""
    try:
        result = predict_capacity(answers.as_list())
    except FileNotFoundError as e:
        raise AIServiceError("Model mood belum tersedia di server.") from e
    return MoodAssessment(**result)


def recommend_tasks(
    tasks: list[dict[str, Any]], assessment: MoodAssessment, today_day: int = 1
) -> list[dict[str, Any]]:
    """
    Pilih & urutkan task hari ini sesuai kapasitas mood, urgensi, dan dependensi.

    Field task yang dipakai (semuanya opsional): `effort_level`, `impact_level`, `day_number`,
    `task_number`, `depends_on`, `status`. Lihat ai_model/mood_predictor.py & CATATAN_INTEGRASI.md.
    `today_day`: hari ke berapa sekarang, dihitung dari hari goal dibuat (hari ke-1).
    """
    return filter_tasks_by_capacity(tasks, assessment.capacity_level, assessment.max_tasks, today_day)
