"""SQLAlchemy entities - task.py"""

from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Task(Base):
    __tablename__ = "task"

    id_task: Mapped[int] = mapped_column(primary_key=True, index=True)
