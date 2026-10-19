"""Pydantic request/response schemas - mood.py (FR-6 & FR-7)"""

from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

CapacityLevel = Literal["LOW", "MEDIUM", "HIGH"]


class MoodAnswers(BaseModel):
    """5 jawaban kuesioner, skala 1-5. Urutan sesuai QuestionnaireAnswer.nomor_questionnaire."""

    q1_focus: int = Field(ge=1, le=5)
    q2_calm: int = Field(ge=1, le=5)
    q3_motivated: int = Field(ge=1, le=5)
    q4_sleep: int = Field(ge=1, le=5)
    q5_readiness: int = Field(ge=1, le=5)

    def as_list(self) -> list[int]:
        return [self.q1_focus, self.q2_calm, self.q3_motivated, self.q4_sleep, self.q5_readiness]


class CapacityProbabilities(BaseModel):
    LOW: float
    MEDIUM: float
    HIGH: float


class MoodAssessment(BaseModel):
    capacity_level: CapacityLevel
    capacity_index: int  # disimpan ke MoodQuestionnaire.hasil_akhir
    confidence: float
    probabilities: CapacityProbabilities
    max_tasks: int
    total_mood_score: int
    recommendation_message: str


class SesiHariIni(BaseModel):
    id_jadwal: int
    waktu_mulai: datetime
    waktu_selesai: datetime


class TaskRekomendasi(BaseModel):
    id_task: int
    id_goal: int
    nama_task: str
    tingkat_effort: Optional[str]
    tingkat_impact: Optional[str]
    deadline: Optional[datetime]
    sesi: list[SesiHariIni]  # sesi `terjadwal` task ini hari ini


class RekomendasiRead(BaseModel):
    """Task terjadwal hari ini dibagi sesuai mood (FR-7). Setelah user setuju, `id_task` dari
    `disarankan_ditunda` dikirim sebagai `ditunda` ke POST /jadwal/susun-ulang (D7: task tidak hilang)."""

    direkomendasikan: list[TaskRekomendasi]  # urut prioritas
    disarankan_ditunda: list[TaskRekomendasi]


class MoodHariIni(BaseModel):
    """Hasil kuesioner mood user pada satu tanggal (respons POST /mood & GET /mood/hari-ini).
    `rekomendasi` dihitung dari jadwal saat request, jadi ikut berubah jika jadwal berubah."""

    id_questionnaire: int
    tanggal: date
    jawaban: MoodAnswers
    hasil: MoodAssessment
    rekomendasi: RekomendasiRead
