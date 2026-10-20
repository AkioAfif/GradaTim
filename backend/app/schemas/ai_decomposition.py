"""AI JSON contract schema

Rencana goal bulanan → mingguan (D4, D11), dengan `effort_level` & `impact_level` per task untuk FR-9
dan mood filter (FR-7).

Catatan: `GoalPlan` dan `WeekTasks` (beserta `PlannedTarget`, `PlannedTask`) dikirim ke LLM sebagai JSON
schema (Structured Outputs, strict mode). Jangan tambahkan default value atau constraint seperti
`ge`/`le` di sini — validasi rentang dilakukan di ai_service setelah parsing.
"""

from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, Field

Level = Literal["low", "medium", "high"]


class GoalDecompositionRequest(BaseModel):
    """Input dari user (FR-1 + FR-3) untuk direncanakan oleh AI."""

    judul_goal: str = Field(min_length=3, max_length=255)
    deskripsi: Optional[str] = Field(default=None, max_length=2000)
    deadline: date
    menit_harian: Optional[int] = Field(
        default=None, ge=15, le=720,
        description="Total waktu luang per hari (menit). Kosong = tidak dibatasi.",
    )


# ============================================================
# RENCANA BULANAN → MINGGUAN (D4, D11)
# ============================================================
# Kerangka tanggal (minggu Senin–Minggu, bulan kalender) dihitung sistem (app/services/rencana.py)
# dan diberikan ke AI; AI hanya mengisi judul & tujuan tiap target serta task minggu ke-1.


class PlannedTask(BaseModel):
    task_number: int = Field(description="Nomor unik task, mulai dari 1, urut sesuai urutan pengerjaan")
    depends_on: list[int] = Field(description="task_number yang harus selesai sebelum task ini dikerjakan")
    task_title: str
    estimated_minutes: int
    effort_level: Level
    impact_level: Level


class PlannedTarget(BaseModel):
    number: int = Field(description="Nomor bulan / minggu persis seperti di kerangka waktu")
    title: str
    description: str = Field(description="Hasil yang ingin dicapai di akhir periode ini, 1 kalimat")


class GoalPlan(BaseModel):
    goal_title: str
    months: list[PlannedTarget]
    weeks: list[PlannedTarget]
    first_week_tasks: list[PlannedTask] = Field(description="Task untuk minggu ke-1 saja")


# Hasil setelah dinormalisasi ai_service (bukan dikirim ke AI)

class TargetMinggu(BaseModel):
    minggu_ke: int
    mulai: date
    akhir: date  # inklusif
    judul: str
    deskripsi: str


class TargetBulan(BaseModel):
    bulan_ke: int
    tahun: int
    bulan: int  # 1–12
    judul: str
    deskripsi: str
    minggu: list[TargetMinggu]


class RencanaGoal(BaseModel):
    bulan: list[TargetBulan]
    task_minggu_ini: list[PlannedTask]  # task minggu ke-1, urut pengerjaan, task_number 1..N


# ============================================================
# RINCIAN TASK PER MINGGU (D11)
# ============================================================
# Minggu ke-2 dst. dirinci saat minggunya tiba (atau mulai Sabtu untuk minggu depan), berdasarkan
# target minggu itu dan progres task minggu-minggu sebelumnya.


class WeekTasks(BaseModel):
    tasks: list[PlannedTask] = Field(description="Task untuk minggu yang diminta saja")


# Input rinci_minggu — dibentuk endpoint dari database, tidak dikirim ke AI sebagai schema

class ProgresTask(BaseModel):
    minggu_ke: int
    judul: str
    menit: Optional[int] = None
    selesai: bool


class RincianMingguRequest(BaseModel):
    judul_goal: str
    deskripsi_goal: Optional[str] = None
    deadline_goal: date
    target: TargetMinggu  # minggu yang dirinci
    target_berikutnya: Optional[TargetMinggu] = None  # konteks saja, supaya AI tidak mencuri target minggu depan
    progres: list[ProgresTask] = Field(default_factory=list)  # task minggu-minggu sebelumnya
    menit_harian: Optional[int] = None
