"""Jembatan tabel kalender (time_constraint, agenda) ↔ objek scheduler (FR-5).

Konversi baris DB ke objek `scheduler` hanya ada di sini, supaya endpoint lain (dekomposisi goal,
nanti jadwal_task) memakai bentuk yang sama.
"""

from datetime import datetime, time, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.agenda import Agenda
from app.models.time_constraint import TimeConstraint
from app.models.user import User
from app.services import scheduler


def rutin_ke_window(rutin: TimeConstraint) -> scheduler.WeeklyWindow:
    return scheduler.WeeklyWindow(rutin.hari_dalam_minggu, rutin.waktu_mulai, rutin.waktu_selesai, label=rutin.nama)


def agenda_ke_busy_block(agenda: Agenda) -> scheduler.BusyBlock:
    return scheduler.BusyBlock(scheduler.Interval(agenda.waktu_mulai, agenda.waktu_selesai), "agenda", agenda.nama)


def kegiatan_rutin_user(db: Session, user: User) -> list[scheduler.WeeklyWindow]:
    query = select(TimeConstraint).where(TimeConstraint.id_user == user.id_user)
    return [rutin_ke_window(r) for r in db.scalars(query)]


def peringatan_bentrok_agenda(db: Session, user: User, agenda: Agenda) -> list[str]:
    """Pesan bentrok agenda dengan kegiatan rutin dan agenda lain user di hari yang sama.

    Hanya peringatan (FR-5): agenda tetap disimpan. Agenda selalu di satu hari kalender,
    jadi cukup memeriksa hari itu saja.
    """
    awal_hari = datetime.combine(agenda.waktu_mulai.date(), time.min)
    akhir_hari = awal_hari + timedelta(days=1)
    agenda_lain = db.scalars(
        select(Agenda).where(
            Agenda.id_user == user.id_user,
            Agenda.id_agenda != agenda.id_agenda,
            Agenda.waktu_mulai < akhir_hari,
            Agenda.waktu_selesai > awal_hari,
        )
    )
    blocks = scheduler.busy_blocks(
        awal_hari,
        akhir_hari,
        routines=kegiatan_rutin_user(db, user),
        agendas=[agenda_ke_busy_block(a) for a in agenda_lain],
    )
    kandidat = scheduler.Interval(agenda.waktu_mulai, agenda.waktu_selesai)
    return [c.message for c in scheduler.find_conflicts(kandidat, blocks)]
