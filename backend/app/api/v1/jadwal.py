"""FR-4, FR-5, FR-11: Kalender & penjadwalan otomatis

Logika penjadwalan ada di app/services/jadwal_service.py; endpoint di sini hanya
mengurus request/response dan commit.
"""

from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.config import settings
from app.models import Goal, JadwalTask, Milestone, Task, User
from app.schemas.jadwal import (
    BlokKalender,
    HasilPenjadwalanRead,
    HasilSusunUlangRead,
    JadwalMingguan,
    SesiRead,
    SusunUlangRequest,
    TaskRingkas,
)
from app.services.jadwal_service import awal_minggu, jadwalkan_goal, muat_konteks, susun_ulang_minggu_ini
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


def _task_ringkas(db: Session, id_tasks: list[int]) -> list[TaskRingkas]:
    return [TaskRingkas(id_task=t.id_task, nama_task=t.nama_task) for t in (db.get(Task, i) for i in id_tasks)]


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


@router.post("/goal/{id_goal}", response_model=HasilPenjadwalanRead)
def jadwalkan_task_goal(
    id_goal: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> HasilPenjadwalanRead:
    """Jadwalkan otomatis task goal yang belum terjadwal ke slot luang minggu ini (FR-4).

    Aman dipanggil berulang: task yang sudah punya sesi tidak dijadwalkan lagi. Task yang tidak
    muat sampai akhir minggu (atau deadline goal) dikembalikan di `tidak_muat`.
    """
    goal = db.get(Goal, id_goal)
    if goal is None or goal.id_user != current_user.id_user:
        # goal milik user lain dijawab sama dengan goal yang tidak ada
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal tidak ditemukan")

    hasil = jadwalkan_goal(db, current_user, goal, datetime.now())
    db.commit()
    return HasilPenjadwalanRead(
        sesi_baru=[_ke_sesi_read(r) for r in hasil.sesi_baru],
        tidak_muat=_task_ringkas(db, hasil.tidak_muat),
    )


@router.post("/susun-ulang", response_model=HasilSusunUlangRead)
def susun_ulang_jadwal(
    payload: SusunUlangRequest = SusunUlangRequest(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> HasilSusunUlangRead:
    """Susun ulang jadwal minggu ini (FR-11): sesi yang terlewat dan task yang ditunda karena mood
    dipindah ke slot kosong berikutnya di minggu yang sama. Sesi lain yang masih valid tidak digeser.

    Body boleh kosong. Dipanggil mis. saat user membuka aplikasi (mengurus sesi terlewat) atau setelah
    user menunda task hari ini.
    """
    ditunda = set(payload.ditunda)
    if ditunda:
        milik_user = set(db.scalars(
            select(Task.id_task)
            .join(Milestone, Task.id_milestone == Milestone.id_milestone)
            .join(Goal, Milestone.id_goal == Goal.id_goal)
            .where(Task.id_task.in_(ditunda), Goal.id_user == current_user.id_user)
        ).all())
        if ditunda - milik_user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task tidak ditemukan")

    hasil = susun_ulang_minggu_ini(db, current_user, datetime.now(), ditunda=sorted(ditunda))
    db.commit()
    return HasilSusunUlangRead(
        dipindah=_task_ringkas(db, hasil.dipindah),
        tidak_muat=_task_ringkas(db, hasil.tidak_muat),
        sesi_baru=[_ke_sesi_read(r) for r in hasil.sesi_baru],
        sesi_dilewati=[_ke_sesi_read(r) for r in hasil.sesi_dilewati],
    )
