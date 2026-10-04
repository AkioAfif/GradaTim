"""Pydantic request/response schemas - mood.py (FR-6 & FR-7)"""

from typing import Literal

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
