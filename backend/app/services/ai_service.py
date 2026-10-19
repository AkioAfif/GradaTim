"""LLM integration & prompting logic

Dua fitur AI GradaTim:
    1. Rencana goal (FR-2, D4, D11) — memecah goal jadi target bulanan → mingguan + task minggu ke-1,
       lalu merinci task minggu-minggu berikutnya sesuai progres, via LLM (default Gemini, lewat
       OpenAI-compatible API + structured output JSON schema). Hasilnya dinormalisasi supaya aman
       dipakai scheduler.
    2. Mood Capacity (FR-6 & FR-7) — wrapper untuk model RandomForest di ai_model/.
"""

from datetime import date
from typing import Any, Optional, TypeVar

from openai import OpenAI, OpenAIError
from pydantic import ValidationError

from ai_model.mood_predictor import filter_tasks_by_capacity, predict_capacity
from app.core import waktu
from app.core.config import settings
from app.schemas.ai_decomposition import (
    GoalDecompositionRequest,
    GoalPlan,
    PlannedTarget,
    PlannedTask,
    RencanaGoal,
    RincianMingguRequest,
    TargetBulan,
    TargetMinggu,
    WeekTasks,
)
from app.schemas.mood import MoodAnswers, MoodAssessment
from app.services.rencana import NAMA_BULAN, BulanRencana, kerangka_rencana

MIN_TASK_MINUTES = 10
MAX_TASK_MINUTES = 240

T = TypeVar("T")


class AIServiceError(Exception):
    """Error yang aman ditampilkan ke user (endpoint bisa map ke HTTP 502/503)."""


# ============================================================
# LLM CLIENT
# ============================================================

def _get_client() -> OpenAI:
    if not settings.LLM_API_KEY:
        raise AIServiceError("LLM_API_KEY belum diset di .env")
    # max_retries: 429/503 (kuota / server Gemini penuh) sering hanya sesaat, SDK retry dengan backoff
    return OpenAI(api_key=settings.LLM_API_KEY, base_url=settings.LLM_BASE_URL, timeout=90, max_retries=4)


def _panggil_llm(client: OpenAI, system_prompt: str, user_prompt: str, response_format: type[T]) -> T:
    """Satu panggilan LLM dengan structured output; semua kegagalan jadi AIServiceError."""
    try:
        completion = client.chat.completions.parse(
            model=settings.LLM_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format=response_format,
        )
    except OpenAIError as e:  # termasuk kuota habis (429), key salah, output terpotong
        raise AIServiceError("Layanan AI sedang tidak tersedia. Coba lagi sebentar lagi.") from e
    except ValidationError as e:  # JSON dari LLM tidak sesuai schema
        raise AIServiceError("Format jawaban AI tidak valid. Coba lagi.") from e

    result = completion.choices[0].message.parsed
    if result is None:  # model menolak (refusal)
        raise AIServiceError("AI tidak bisa memproses goal ini. Coba ubah judul atau deskripsinya.")
    return result


# ============================================================
# RENCANA BULANAN → MINGGUAN (D4, D11)
# ============================================================

# Aturan task yang sama untuk rencana awal (minggu ke-1) dan rincian minggu berikutnya
_ATURAN_TASK = """- Tulis dalam Bahasa Indonesia, singkat, diawali kata kerja (contoh: "Install Docker Desktop & verifikasi CLI").
- Setiap task harus bisa langsung dikerjakan tanpa dipecah lagi, dan hasilnya jelas terlihat.
- estimated_minutes realistis, antara 10 dan 240 menit per task.
- effort_level: seberapa berat usaha/energi mental task tersebut (low/medium/high).
- impact_level: seberapa besar kontribusi task terhadap tercapainya goal (low/medium/high).
- task_number: nomor unik 1, 2, 3, ... sesuai urutan pengerjaan.
- depends_on: task_number yang WAJIB selesai sebelum task ini bisa dikerjakan (hanya boleh menunjuk
  task dengan nomor lebih kecil). Kosongkan ([]) jika tidak ada prasyarat.
- Jangan membuat pengguna kewalahan: lebih baik task kecil yang konsisten daripada task besar yang menakutkan."""

PLAN_SYSTEM_PROMPT = """Kamu adalah perencana target pribadi untuk aplikasi GradaTim.
Tugasmu menyusun rencana bertahap untuk satu goal besar: target bulanan → target mingguan,
lalu merinci task konkret HANYA untuk minggu ke-1. Task minggu-minggu berikutnya dirinci nanti
sesuai progres pengguna, jadi jangan dibuat sekarang.

Aturan kerangka:
- Ikuti kerangka waktu yang diberikan PERSIS: satu entri `months` untuk setiap bulan dan satu entri
  `weeks` untuk setiap minggu, dengan `number` sama seperti di kerangka. Jangan menambah atau menghapus.
- Target bulanan merangkum target mingguan di dalamnya; target mingguan berurutan dan saling membangun.
- Sesuaikan isi target dengan panjang periodenya: minggu / bulan yang pendek mendapat target yang lebih kecil.
- Sisakan minggu terakhir untuk mengulang / memantapkan bila waktunya longgar.
- title singkat dan spesifik (contoh: "Kuasai tenses dasar"); description = hasil yang ingin dicapai, 1 kalimat.

Aturan task minggu ke-1:
- Task harus mewujudkan target minggu ke-1, dan muat di jumlah hari minggu ke-1.
- Buat 2-10 task, urut sesuai urutan pengerjaan.
""" + _ATURAN_TASK


def _tanggal(d: date) -> str:
    return f"{d.day} {NAMA_BULAN[d.month - 1][:3]} {d.year}"


def _kerangka_teks(kerangka: list[BulanRencana]) -> str:
    baris = []
    for b in kerangka:
        baris.append(f"Bulan {b.bulan_ke} — {b.nama}")
        for m in b.minggu:
            baris.append(f"  Minggu {m.minggu_ke}: {_tanggal(m.mulai)} – {_tanggal(m.akhir)} ({m.jumlah_hari} hari)")
    return "\n".join(baris)


def _build_plan_prompt(request: GoalDecompositionRequest, today: date, kerangka: list[BulanRencana]) -> str:
    minggu_pertama = kerangka[0].minggu[0]
    lines = [
        f"Goal: {request.judul_goal}",
        f"Deskripsi: {request.deskripsi or '-'}",
        f"Tanggal hari ini: {today.isoformat()}",
        f"Deadline: {request.deadline.isoformat()}",
        "",
        "Kerangka waktu (WAJIB diikuti):",
        _kerangka_teks(kerangka),
        "",
        f"Minggu ke-1 hanya {minggu_pertama.jumlah_hari} hari (sampai {_tanggal(minggu_pertama.akhir)}).",
    ]
    if request.menit_harian:
        lines.append(
            f"Waktu luang pengguna: maksimal {request.menit_harian} menit per hari, jadi total estimated_minutes "
            f"task minggu ke-1 tidak boleh melebihi {request.menit_harian * minggu_pertama.jumlah_hari} menit."
        )
    return "\n".join(lines)


def _normalize_planned_tasks(tasks: list[PlannedTask]) -> list[PlannedTask]:
    """Clamp durasi, nomori ulang 1..N sesuai urutan, dan bersihkan depends_on: buang referensi ke
    task yang tidak ada / diri sendiri / task yang lebih belakang (mencegah dependensi melingkar)."""
    tasks = sorted(tasks, key=lambda t: t.task_number)
    old_numbers = [t.task_number for t in tasks]
    numbers_unique = len(set(old_numbers)) == len(old_numbers)
    renumber = {old: new for new, old in enumerate(old_numbers, start=1)} if numbers_unique else {}
    for new_number, task in enumerate(tasks, start=1):
        task.estimated_minutes = min(max(task.estimated_minutes, MIN_TASK_MINUTES), MAX_TASK_MINUTES)
        task.task_number = new_number
        # nomor dari LLM duplikat → tidak bisa dipetakan dengan aman, dependensi dibuang
        task.depends_on = sorted({renumber[d] for d in task.depends_on if d in renumber and renumber[d] < new_number})
    return tasks


def _judul(target: Optional[PlannedTarget], cadangan: str) -> tuple[str, str]:
    if target is None:
        return cadangan, ""
    return target.title.strip() or cadangan, target.description.strip()


def _normalize_plan(result: GoalPlan, kerangka: list[BulanRencana]) -> RencanaGoal:
    """Tempelkan judul dari AI ke kerangka buatan sistem. Tanggal & jumlah target selalu dari kerangka;
    target yang tidak diisi AI diberi judul cadangan, nomor yang tidak ada di kerangka dibuang."""
    if not result.first_week_tasks:
        raise AIServiceError("AI tidak menghasilkan task apa pun. Coba perjelas deskripsi goal-mu.")
    target_bulan: dict[int, PlannedTarget] = {}
    for t in result.months:
        target_bulan.setdefault(t.number, t)  # nomor duplikat → ambil yang pertama
    target_minggu: dict[int, PlannedTarget] = {}
    for t in result.weeks:
        target_minggu.setdefault(t.number, t)

    bulan = []
    for b in kerangka:
        minggu = []
        for m in b.minggu:
            judul, deskripsi = _judul(target_minggu.get(m.minggu_ke), f"Target minggu ke-{m.minggu_ke}")
            minggu.append(TargetMinggu(minggu_ke=m.minggu_ke, mulai=m.mulai, akhir=m.akhir, judul=judul,
                                       deskripsi=deskripsi))
        judul, deskripsi = _judul(target_bulan.get(b.bulan_ke), f"Target {b.nama}")
        bulan.append(TargetBulan(bulan_ke=b.bulan_ke, tahun=b.tahun, bulan=b.bulan, judul=judul,
                                 deskripsi=deskripsi, minggu=minggu))
    return RencanaGoal(bulan=bulan, task_minggu_ini=_normalize_planned_tasks(result.first_week_tasks))


def rencanakan_goal(
    request: GoalDecompositionRequest,
    today: Optional[date] = None,
    client: Optional[OpenAI] = None,
) -> RencanaGoal:
    """
    Susun rencana goal: target bulanan → target mingguan (seluruh durasi goal) + task minggu ke-1 (D4, D11).

    Kerangka tanggal dihitung sistem (`rencana.kerangka_rencana`): minggu Senin–Minggu mulai hari ini,
    dikelompokkan per bulan kalender. AI hanya mengisi judul & tujuan serta task minggu ke-1.

    Args:
        request: judul, deskripsi, deadline, dan (opsional) menit luang per hari
        today: override tanggal hari ini (untuk testing). Default: tanggal hari ini di WIB,
            bukan tanggal server (di container Docker jam server = UTC)
        client: override LLM client (untuk testing)

    Raises:
        AIServiceError: deadline sudah lewat, API gagal, atau output AI tidak bisa dipakai
    """
    today = today or waktu.hari_ini()
    if request.deadline < today:
        raise AIServiceError("Deadline sudah lewat. Pilih tanggal hari ini atau setelahnya.")
    kerangka = kerangka_rencana(today, request.deadline)
    result = _panggil_llm(
        client or _get_client(), PLAN_SYSTEM_PROMPT, _build_plan_prompt(request, today, kerangka), GoalPlan
    )
    return _normalize_plan(result, kerangka)


# ============================================================
# RINCIAN TASK PER MINGGU (D11)
# ============================================================

WEEK_SYSTEM_PROMPT = """Kamu adalah perencana target pribadi untuk aplikasi GradaTim.
Pengguna sedang mengejar satu goal besar yang sudah dipecah menjadi target mingguan. Tugasmu merinci
task konkret untuk SATU minggu saja, berdasarkan target minggu itu dan progres pengguna sejauh ini.

Aturan minggu ini:
- Task harus mewujudkan target minggu ini, dan muat di sisa hari minggu ini.
- Lanjutkan dari task yang sudah selesai; jangan mengulang task yang sudah selesai.
- Task lama yang belum selesai tetap ada di jadwal pengguna, jadi jangan buat ulang task yang sama.
  Bila banyak yang tertinggal, buat task minggu ini lebih sedikit dan lebih ringan.
- Jangan mengerjakan target minggu berikutnya lebih dulu.
- Buat 1-10 task, urut sesuai urutan pengerjaan.
""" + _ATURAN_TASK

MENIT_MINIMAL_MINGGU = 30  # di bawah ini, waktu minggu ini dianggap sudah penuh oleh task lama


def _build_week_prompt(request: RincianMingguRequest, mulai: date) -> str:
    t = request.target
    hari = (t.akhir - mulai).days + 1
    lines = [
        f"Goal: {request.judul_goal}",
        f"Deskripsi: {request.deskripsi_goal or '-'}",
        f"Deadline goal: {request.deadline_goal.isoformat()}",
        "",
        f"Target minggu ke-{t.minggu_ke} ({_tanggal(t.mulai)} – {_tanggal(t.akhir)}): {t.judul}",
        f"Hasil yang ingin dicapai: {t.deskripsi or '-'}",
        f"Sisa waktu minggu ini: {hari} hari ({_tanggal(mulai)} – {_tanggal(t.akhir)}).",
    ]
    if request.target_berikutnya:
        lines.append(f"Target minggu berikutnya (JANGAN dikerjakan sekarang): {request.target_berikutnya.judul}")

    lines += ["", "Progres task minggu-minggu sebelumnya ([x] = selesai, [ ] = belum):"]
    if request.progres:
        for p in request.progres:
            menit = f" ({p.menit} menit)" if p.menit else ""
            lines.append(f"- [{'x' if p.selesai else ' '}] Minggu {p.minggu_ke}: {p.judul}{menit}")
        selesai = sum(p.selesai for p in request.progres)
        lines.append(f"Selesai {selesai} dari {len(request.progres)} task.")
    else:
        lines.append("- (belum ada task sebelumnya)")

    if request.menit_harian:
        batas = request.menit_harian * hari
        tertunda = sum(p.menit or 0 for p in request.progres if not p.selesai)
        sisa = batas - tertunda
        lines.append("")
        if sisa < MENIT_MINIMAL_MINGGU:
            lines.append(f"Waktu luang minggu ini ({batas} menit) sudah hampir habis oleh task lama yang belum selesai "
                         f"({tertunda} menit): buat 1 task ringan saja, maksimal {MENIT_MINIMAL_MINGGU} menit.")
        elif tertunda:
            lines.append(f"Waktu luang pengguna: maksimal {request.menit_harian} menit per hari ({batas} menit untuk "
                         f"{hari} hari), {tertunda} menit di antaranya masih untuk task lama yang belum selesai, jadi "
                         f"total estimated_minutes task baru tidak boleh melebihi {sisa} menit.")
        else:
            lines.append(f"Waktu luang pengguna: maksimal {request.menit_harian} menit per hari, jadi total "
                         f"estimated_minutes task tidak boleh melebihi {batas} menit.")
    return "\n".join(lines)


def rinci_minggu(
    request: RincianMingguRequest,
    today: Optional[date] = None,
    client: Optional[OpenAI] = None,
) -> list[PlannedTask]:
    """
    Rinci task konkret untuk satu target mingguan, berdasarkan progres minggu-minggu sebelumnya (D11).

    Bila minggunya sedang berjalan, hanya sisa hari mulai `today` yang dihitung; bila minggu depan
    (dirinci lebih awal), seluruh minggu dihitung.

    Args:
        request: goal, target minggu yang dirinci (+ target berikutnya), progres, menit luang per hari
        today: override tanggal hari ini (untuk testing). Default: tanggal hari ini di WIB
        client: override LLM client (untuk testing)

    Returns:
        Task urut pengerjaan, task_number 1..N, depends_on hanya ke task di daftar ini.

    Raises:
        AIServiceError: minggunya sudah lewat, API gagal, atau AI tidak menghasilkan task
    """
    today = today or waktu.hari_ini()
    if today > request.target.akhir:
        raise AIServiceError("Minggu ini sudah lewat, tidak bisa dirinci lagi.")
    mulai = max(today, request.target.mulai)
    result = _panggil_llm(
        client or _get_client(), WEEK_SYSTEM_PROMPT, _build_week_prompt(request, mulai), WeekTasks
    )
    if not result.tasks:
        raise AIServiceError("AI tidak menghasilkan task apa pun. Coba lagi.")
    return _normalize_planned_tasks(result.tasks)


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
