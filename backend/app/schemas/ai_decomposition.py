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
