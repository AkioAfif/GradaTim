"""SQLAlchemy entities - mood_questionnaire.py"""

from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class MoodQuestionnaire(Base):
    __tablename__ = "mood_questionnaire"

    id_questionnaire: Mapped[int] = mapped_column(primary_key=True, index=True)
