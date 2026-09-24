"""SQLAlchemy entities - questionnaire_answer.py"""

from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class QuestionnaireAnswer(Base):
    __tablename__ = "questionnaire_answer"

    id_answer: Mapped[int] = mapped_column(primary_key=True, index=True)
