"""SQLAlchemy entities - time_constraint.py"""

from datetime import date, datetime, time
from typing import Optional

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class TimeConstraint(Base):
    __tablename__ = "time_constraint"

    id_constraint: Mapped[int] = mapped_column(primary_key=True, index=True)
    id_user: Mapped[int] = mapped_column(ForeignKey("user.id_user"), index=True)
    hari_dalam_minggu: Mapped[int] = mapped_column(Integer)  # 0=Senin ... 6=Minggu
    waktu_mulai: Mapped[time] = mapped_column(Time)
    waktu_selesai: Mapped[time] = mapped_column(Time)

    user: Mapped["User"] = relationship(back_populates="time_constraints")
