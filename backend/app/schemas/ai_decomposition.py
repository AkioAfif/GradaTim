"""AI JSON contract schema

Mengikuti kontrak di docs/PROJECT_SPECIFICATIONS.md (bagian 5A), ditambah
`effort_level` & `impact_level` per task untuk FR-9 dan mood filter (FR-7).

Catatan: model `Decomposed*` dikirim ke OpenAI sebagai JSON schema (Structured
Outputs, strict mode). Jangan tambahkan default value atau constraint seperti
`ge`/`le` di sini — validasi rentang dilakukan di ai_service setelah parsing.
"""

from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, Field

Level = Literal["low", "medium", "high"]


class DecomposedTask(BaseModel):
    task_number: int = Field(description="Nomor unik task di seluruh goal, mulai dari 1")
    depends_on: list[int] = Field(description="task_number yang harus selesai sebelum task ini dikerjakan")
    task_title: str
    day_number: int = Field(description="Hari ke berapa task dikerjakan, mulai dari 1")
    estimated_minutes: int
    effort_level: Level
    impact_level: Level


class DecomposedMilestone(BaseModel):
    milestone_title: str
    order: int = Field(description="Urutan milestone, mulai dari 1")
    tasks: list[DecomposedTask]


class GoalDecomposition(BaseModel):
    goal_title: str
    estimated_total_days: int
    milestones: list[DecomposedMilestone]


class GoalDecompositionRequest(BaseModel):
    """Input dari user (FR-1 + FR-3) untuk dipecah oleh AI."""

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
