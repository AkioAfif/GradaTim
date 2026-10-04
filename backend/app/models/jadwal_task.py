"""SQLAlchemy entities - jadwal_task.py"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class JadwalTask(Base):
    """Satu sesi pengerjaan task di kalender. Satu task boleh dicicil ke beberapa sesi."""

    __tablename__ = "jadwal_task"

    id_jadwal: Mapped[int] = mapped_column(primary_key=True, index=True)
    id_task: Mapped[int] = mapped_column(ForeignKey("task.id_task"), index=True)
    waktu_mulai: Mapped[datetime] = mapped_column(DateTime)
    waktu_selesai: Mapped[datetime] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(20), default="terjadwal")

    task: Mapped["Task"] = relationship(back_populates="jadwal")
