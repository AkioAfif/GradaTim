"""SQLAlchemy entities - mood_questionnaire.py"""

from datetime import date, datetime, time
from typing import Optional

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class MoodQuestionnaire(Base):
    __tablename__ = "mood_questionnaire"

    id_questionnaire: Mapped[int] = mapped_column(primary_key=True, index=True)
    id_user: Mapped[int] = mapped_column(ForeignKey("user.id_user"), index=True)
    tanggal: Mapped[date] = mapped_column(Date)
    hasil_akhir: Mapped[Optional[int]] = mapped_column(Integer)

    user: Mapped["User"] = relationship(back_populates="mood_questionnaires")
    answers: Mapped[list["QuestionnaireAnswer"]] = relationship(
        back_populates="questionnaire", cascade="all, delete-orphan"
    )
