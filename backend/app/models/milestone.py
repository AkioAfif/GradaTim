"""SQLAlchemy entities - milestone.py"""

from datetime import date, datetime, time
from typing import Optional

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Milestone(Base):
    __tablename__ = "milestone"

    id_milestone: Mapped[int] = mapped_column(primary_key=True, index=True)
    id_goal: Mapped[int] = mapped_column(ForeignKey("goal.id_goal"), index=True)
    id_parent_milestone: Mapped[Optional[int]] = mapped_column(ForeignKey("milestone.id_milestone"), index=True)
    judul_milestone: Mapped[str] = mapped_column(String(255))
    deskripsi: Mapped[Optional[str]] = mapped_column(Text)
    deadline: Mapped[Optional[datetime]] = mapped_column(DateTime)
    urutan: Mapped[int] = mapped_column(Integer, default=0)  # urutan di antara milestone dengan parent yang sama
    status: Mapped[str] = mapped_column(String(20), default="pending")
    tipe: Mapped[Optional[str]] = mapped_column(String(10))  # bulanan | mingguan | NULL (milestone biasa)

    goal: Mapped["Goal"] = relationship(back_populates="milestones")
    tasks: Mapped[list["Task"]] = relationship(back_populates="milestone", cascade="all, delete-orphan")
    parent_milestone: Mapped[Optional["Milestone"]] = relationship(
        back_populates="sub_milestones", remote_side=[id_milestone]
    )
    sub_milestones: Mapped[list["Milestone"]] = relationship(
        back_populates="parent_milestone", cascade="all, delete-orphan", order_by="Milestone.urutan"
    )
