"""Penghubung database ↔ penjadwal (scheduler.py)

scheduler.py berisi logika murni tanpa database. Modul ini:
    - membaca kegiatan rutin, agenda, dan sesi jadwal user dari database
      lalu mengubahnya ke bentuk yang dipahami scheduler  (tahap A — modul ini)
    - menyimpan hasil penjadwalan & re-planning ke tabel jadwal_task  (tahap B, C)

Dipanggil dari endpoint API; endpoint tidak perlu tahu detail scheduler.
Keputusan desain: docs/KEPUTUSAN_DESAIN_PENJADWALAN.md
"""

from dataclasses import dataclass, field
from datetime import datetime, time, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.core.config import settings
from app.models import Agenda, Goal, JadwalTask, Milestone, Task, TimeConstraint, User
from app.services.scheduler import (
    BusyBlock,
    Interval,
    Session,
    WeeklyWindow,
    busy_blocks,
    free_slots,
)

# Nilai kolom jadwal_task.status. Sesi `dilewati` hanya riwayat — tidak dianggap sibuk & tidak dijadwalkan ulang lagi.
STATUS_TERJADWAL = "terjadwal"
STATUS_SELESAI = "selesai"
STATUS_DILEWATI = "dilewati"

TASK_STATUS_DONE = "done"  # Task.status yang berarti task selesai
DEFAULT_DURASI_MENIT = 30  # untuk task tanpa durasi_estimasi


def awal_minggu(waktu: datetime) -> datetime:
    """Senin 00:00 dari minggu yang memuat `waktu` (unit perencanaan = minggu, D7/D11)."""
    return datetime.combine(waktu.date() - timedelta(days=waktu.weekday()), time.min)


def jam_aktif() -> list[WeeklyWindow]:
    """Jam aktif harian dari config, sama untuk tiap hari (D10)."""
    return [WeeklyWindow(hari, settings.JAM_AKTIF_MULAI, settings.JAM_AKTIF_SELESAI) for hari in range(7)]


# ============================================================
# BACA DARI DATABASE
# ============================================================

def kegiatan_rutin(db: DbSession, user: User) -> list[WeeklyWindow]:
    """Kegiatan rutin mingguan user (tabel time_constraint)."""
    rows = db.scalars(select(TimeConstraint).where(TimeConstraint.id_user == user.id_user)).all()
    return [WeeklyWindow(r.hari_dalam_minggu, r.waktu_mulai, r.waktu_selesai, label=r.nama) for r in rows]


def agenda_user(db: DbSession, user: User, mulai: datetime, akhir: datetime) -> list[BusyBlock]:
    """Agenda sekali-jalan user yang beririsan dengan [mulai, akhir)."""
    rows = db.scalars(
        select(Agenda).where(
            Agenda.id_user == user.id_user,
            Agenda.waktu_selesai > mulai,
            Agenda.waktu_mulai < akhir,
        )
    ).all()
    return [BusyBlock(Interval(r.waktu_mulai, r.waktu_selesai), "agenda", r.nama) for r in rows]


def sesi_user(db: DbSession, user: User, mulai: datetime, akhir: datetime) -> list[JadwalTask]:
    """Sesi jadwal_task milik user (lewat task → milestone → goal) yang beririsan dengan [mulai, akhir).
    Sesi berstatus `dilewati` tidak ikut (hanya riwayat)."""
    return list(db.scalars(
        select(JadwalTask)
        .join(Task, JadwalTask.id_task == Task.id_task)
        .join(Milestone, Task.id_milestone == Milestone.id_milestone)
        .join(Goal, Milestone.id_goal == Goal.id_goal)
        .where(
            Goal.id_user == user.id_user,
            JadwalTask.status != STATUS_DILEWATI,
            JadwalTask.waktu_selesai > mulai,
            JadwalTask.waktu_mulai < akhir,
        )
        .order_by(JadwalTask.waktu_mulai)
    ).all())


def ke_session(row: JadwalTask) -> Session:
    """Baris jadwal_task → Session milik scheduler (task_number = id_task)."""
    return Session(row.id_task, Interval(row.waktu_mulai, row.waktu_selesai), done=row.status == STATUS_SELESAI)


@dataclass
class KonteksJadwal:
    """Semua yang dibutuhkan scheduler untuk satu user di rentang [mulai, akhir)."""

    mulai: datetime
    akhir: datetime
    rutin: list[WeeklyWindow] = field(default_factory=list)
    agenda: list[BusyBlock] = field(default_factory=list)
    sesi: list[JadwalTask] = field(default_factory=list)
    # jam aktif − kegiatan rutin − agenda (sesi task BELUM dikurangkan; replan butuh bentuk ini)
    slot_luang: list[Interval] = field(default_factory=list)

    @property
    def sessions(self) -> list[Session]:
        return [ke_session(r) for r in self.sesi]

    def blok_sibuk(self) -> list[BusyBlock]:
        """Semua jam sibuk (rutin, agenda, sesi task) — untuk cek bentrok FR-5."""
        return busy_blocks(self.mulai, self.akhir, self.rutin, self.agenda, self.sessions)


def muat_konteks(db: DbSession, user: User, mulai: datetime, akhir: datetime) -> KonteksJadwal:
    rutin = kegiatan_rutin(db, user)
    agenda = agenda_user(db, user, mulai, akhir)
    return KonteksJadwal(
        mulai=mulai,
        akhir=akhir,
        rutin=rutin,
        agenda=agenda,
        sesi=sesi_user(db, user, mulai, akhir),
        slot_luang=free_slots(jam_aktif(), mulai, akhir, rutin, busy=[a.interval for a in agenda]),
    )
