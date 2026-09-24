"""SQLAlchemy entities - questionnaire_answer.py"""

from datetime import date, datetime, time
from typing import Optional

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class QuestionnaireAnswer(Base):
    __tablename__ = "questionnaire_answer"

    id_answer: Mapped[int] = mapped_column(primary_key=True, index=True)
    id_questionnaire: Mapped[int] = mapped_column(ForeignKey("mood_questionnaire.id_questionnaire"), index=True)
    nomor_questionnaire: Mapped[int] = mapped_column(Integer)  # pertanyaan ke-1..5
    nilai_jawaban: Mapped[int] = mapped_column(Integer)

    questionnaire: Mapped["MoodQuestionnaire"] = relationship(back_populates="answers")
