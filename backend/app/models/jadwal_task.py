"""SQLAlchemy entities - jadwal_task.py"""

from datetime import datetime

from typing import Any, Optional

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, false
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.status import JADWAL_TERJADWAL
from app.db.base import Base


class JadwalTask(Base):
    """Satu sesi pengerjaan task di kalender. Satu task boleh dicicil ke beberapa sesi."""

    __tablename__ = "jadwal_task"

    id_jadwal: Mapped[int] = mapped_column(primary_key=True, index=True)
    id_task: Mapped[int] = mapped_column(ForeignKey("task.id_task"), index=True)
    waktu_mulai: Mapped[datetime] = mapped_column(DateTime)
    waktu_selesai: Mapped[datetime] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(20), default=JADWAL_TERJADWAL)
    # Data untuk model personalisasi (docs/AI.md §2)
    dipindah: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())  # dipindah manual user
    eksplorasi: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())  # slot dipilih acak
    fitur: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)  # snapshot fitur saat dijadwalkan

    task: Mapped["Task"] = relationship(back_populates="jadwal")
