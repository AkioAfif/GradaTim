"""FR-4, FR-5, FR-11: Kalender & penjadwalan otomatis

Logika penjadwalan ada di app/services/jadwal_service.py; endpoint di sini hanya
mengurus request/response dan commit.
"""

from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.config import settings
from app.models import JadwalTask, User
from app.schemas.jadwal import BlokKalender, JadwalMingguan, SesiRead
from app.services.jadwal_service import awal_minggu, muat_konteks
from app.services.scheduler import busy_blocks

router = APIRouter()


def _ke_sesi_read(row: JadwalTask) -> SesiRead:
    return SesiRead(
        id_jadwal=row.id_jadwal,
        id_task=row.id_task,
        id_goal=row.task.milestone.id_goal,
        nama_task=row.task.nama_task,
        waktu_mulai=row.waktu_mulai,
        waktu_selesai=row.waktu_selesai,
        status=row.status,
    )


@router.get("", response_model=JadwalMingguan)
def lihat_jadwal_mingguan(
    minggu: Optional[date] = Query(None, description="Tanggal mana pun di minggu yang diminta; default minggu ini"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> JadwalMingguan:
    """Isi kalender satu minggu (Senin–Minggu): kegiatan rutin, agenda, dan sesi task.
    Sesi berstatus `dilewati` tidak ditampilkan (hanya riwayat)."""
    mulai = awal_minggu(datetime.combine(minggu, datetime.min.time()) if minggu else datetime.now())
    akhir = mulai + timedelta(days=7)
    konteks = muat_konteks(db, current_user, mulai, akhir)
    blok_rutin = busy_blocks(mulai, akhir, routines=konteks.rutin)
    return JadwalMingguan(
        mulai=mulai,
        akhir=akhir,
        jam_aktif_mulai=settings.JAM_AKTIF_MULAI,
        jam_aktif_selesai=settings.JAM_AKTIF_SELESAI,
        kegiatan_rutin=[BlokKalender(nama=b.label, waktu_mulai=b.interval.start, waktu_selesai=b.interval.end)
                        for b in blok_rutin],
        agenda=[BlokKalender(nama=b.label, waktu_mulai=b.interval.start, waktu_selesai=b.interval.end)
                for b in sorted(konteks.agenda, key=lambda b: b.interval.start)],
        sesi=[_ke_sesi_read(r) for r in konteks.sesi],
    )
