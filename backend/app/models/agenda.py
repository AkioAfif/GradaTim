"""SQLAlchemy entities - agenda.py"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Agenda(Base):
    """Acara sekali jalan di tanggal tertentu (FR-5). Kegiatan rutin mingguan ada di `time_constraint`."""

    __tablename__ = "agenda"

    id_agenda: Mapped[int] = mapped_column(primary_key=True, index=True)
    id_user: Mapped[int] = mapped_column(ForeignKey("user.id_user"), index=True)
    nama: Mapped[str] = mapped_column(String(100))
    waktu_mulai: Mapped[datetime] = mapped_column(DateTime)
    waktu_selesai: Mapped[datetime] = mapped_column(DateTime)

    user: Mapped["User"] = relationship(back_populates="agenda")
