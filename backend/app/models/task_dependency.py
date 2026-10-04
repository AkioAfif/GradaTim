"""SQLAlchemy entities - task_dependency.py"""

from sqlalchemy import CheckConstraint, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class TaskDependency(Base):
    """Task `id_task` baru bisa dikerjakan setelah `id_task_prasyarat` selesai.

    Beda dengan `Task.id_parent_task` (hierarki sub-task): ini urutan prasyarat antar task.
    """

    __tablename__ = "task_dependency"
    __table_args__ = (CheckConstraint("id_task <> id_task_prasyarat", name="ck_task_dependency_bukan_diri_sendiri"),)

    id_task: Mapped[int] = mapped_column(ForeignKey("task.id_task"), primary_key=True)
    id_task_prasyarat: Mapped[int] = mapped_column(ForeignKey("task.id_task"), primary_key=True, index=True)

    task: Mapped["Task"] = relationship(back_populates="prasyarat", foreign_keys=[id_task])
    task_prasyarat: Mapped["Task"] = relationship(back_populates="dependen", foreign_keys=[id_task_prasyarat])
