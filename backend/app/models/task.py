"""SQLAlchemy entities - task.py"""

from datetime import date, datetime, time
from typing import Optional

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Task(Base):
    __tablename__ = "task"

    id_task: Mapped[int] = mapped_column(primary_key=True, index=True)
    id_milestone: Mapped[int] = mapped_column(ForeignKey("milestone.id_milestone"), index=True)
    id_parent_task: Mapped[Optional[int]] = mapped_column(ForeignKey("task.id_task"), index=True)
    nama_task: Mapped[str] = mapped_column(String(255))
    deskripsi: Mapped[Optional[str]] = mapped_column(Text)
    deadline: Mapped[Optional[datetime]] = mapped_column(DateTime)
    durasi_estimasi: Mapped[Optional[int]] = mapped_column(Integer)  # menit
    status: Mapped[str] = mapped_column(String(20), default="pending")

    milestone: Mapped["Milestone"] = relationship(back_populates="tasks")
    parent_task: Mapped[Optional["Task"]] = relationship(back_populates="sub_tasks", remote_side=[id_task])
    sub_tasks: Mapped[list["Task"]] = relationship(back_populates="parent_task", cascade="all, delete-orphan")
