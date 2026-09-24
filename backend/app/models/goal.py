"""SQLAlchemy entities - goal.py"""

from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Goal(Base):
    __tablename__ = "goal"

    id_goal: Mapped[int] = mapped_column(primary_key=True, index=True)
