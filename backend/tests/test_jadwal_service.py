"""Unit tests untuk app/services/jadwal_service.py (database SQLite in-memory)"""

from datetime import datetime, time

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401 — daftarkan semua tabel ke Base.metadata
from app.db.base import Base
from app.models import Agenda, Goal, JadwalTask, Milestone, Task, TimeConstraint, User
from app.services import jadwal_service
from app.services.jadwal_service import (
    STATUS_DILEWATI,
    STATUS_SELESAI,
    STATUS_TERJADWAL,
    agenda_user,
    awal_minggu,
    jam_aktif,
    kegiatan_rutin,
    ke_session,
    muat_konteks,
    sesi_user,
)
from app.services.scheduler import Interval

SEN, SEL, RAB = 0, 1, 2
MINGGU_INI = (datetime(2026, 10, 5), datetime(2026, 10, 12))  # Senin 5 - Senin 12 Okt


def dt(day, hour, minute=0):
    return datetime(2026, 10, day, hour, minute)


@pytest.fixture
def db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


def buat_user(db, email="argya@example.com"):
    user = User(nama="Argya", email=email, password="hash")
    goal = Goal(user=user, judul_goal="Belajar Docker")
    milestone = Milestone(goal=goal, judul_milestone="Dasar Docker")
    tasks = [Task(milestone=milestone, nama_task=f"Task {i}", durasi_estimasi=60) for i in range(3)]
    db.add_all([user, goal, milestone, *tasks])
    db.flush()
    return user, tasks


@pytest.fixture
def user_lengkap(db):
    """User dengan kegiatan rutin, agenda, dan sesi; plus user lain sebagai pembanding."""
    user, tasks = buat_user(db)
    db.add_all([
        TimeConstraint(user=user, nama="Kuliah", hari_dalam_minggu=SEN, waktu_mulai=time(8), waktu_selesai=time(15)),
        TimeConstraint(user=user, nama="Gym", hari_dalam_minggu=RAB, waktu_mulai=time(16), waktu_selesai=time(18)),
        Agenda(user=user, nama="Rapat himpunan", waktu_mulai=dt(6, 19), waktu_selesai=dt(6, 21)),
        Agenda(user=user, nama="Agenda minggu depan", waktu_mulai=dt(13, 19), waktu_selesai=dt(13, 21)),
        JadwalTask(task=tasks[0], waktu_mulai=dt(5, 15), waktu_selesai=dt(5, 16), status=STATUS_SELESAI),
        JadwalTask(task=tasks[1], waktu_mulai=dt(6, 15), waktu_selesai=dt(6, 16), status=STATUS_DILEWATI),
        JadwalTask(task=tasks[1], waktu_mulai=dt(7, 15), waktu_selesai=dt(7, 16), status=STATUS_TERJADWAL),
        JadwalTask(task=tasks[2], waktu_mulai=dt(14, 15), waktu_selesai=dt(14, 16), status=STATUS_TERJADWAL),
    ])

    lain, tasks_lain = buat_user(db, email="akio@example.com")
    db.add_all([
        TimeConstraint(user=lain, nama="Kerja", hari_dalam_minggu=SEL, waktu_mulai=time(9), waktu_selesai=time(17)),
        Agenda(user=lain, nama="Agenda Akio", waktu_mulai=dt(6, 10), waktu_selesai=dt(6, 11)),
        JadwalTask(task=tasks_lain[0], waktu_mulai=dt(6, 15), waktu_selesai=dt(6, 16)),
    ])
    db.flush()
    return user, tasks


# ------------------------------------------------------------
# UTILITAS
# ------------------------------------------------------------

def test_awal_minggu():
    assert awal_minggu(dt(7, 13, 45)) == datetime(2026, 10, 5)  # Rabu → Senin 00:00
    assert awal_minggu(dt(5, 0)) == datetime(2026, 10, 5)
    assert awal_minggu(dt(11, 23)) == datetime(2026, 10, 5)  # Minggu masih minggu yang sama


def test_jam_aktif_from_config(monkeypatch):
    monkeypatch.setattr(jadwal_service.settings, "JAM_AKTIF_MULAI", time(7))
    monkeypatch.setattr(jadwal_service.settings, "JAM_AKTIF_SELESAI", time(21))
    windows = jam_aktif()
    assert len(windows) == 7
    assert {(w.start, w.end) for w in windows} == {(time(7), time(21))}


# ------------------------------------------------------------
# BACA DARI DATABASE
# ------------------------------------------------------------

def test_kegiatan_rutin_only_own_with_labels(db, user_lengkap):
    user, _ = user_lengkap
    rutin = kegiatan_rutin(db, user)
    assert sorted((w.weekday, w.label) for w in rutin) == [(SEN, "Kuliah"), (RAB, "Gym")]


def test_agenda_user_filters_user_and_range(db, user_lengkap):
    user, _ = user_lengkap
    agenda = agenda_user(db, user, *MINGGU_INI)
    assert [(a.label, a.kind) for a in agenda] == [("Rapat himpunan", "agenda")]
    assert agenda[0].interval == Interval(dt(6, 19), dt(6, 21))


def test_sesi_user_excludes_other_users_skipped_and_out_of_range(db, user_lengkap):
    user, tasks = user_lengkap
    sesi = sesi_user(db, user, *MINGGU_INI)
    assert [(s.id_task, s.waktu_mulai) for s in sesi] == [
        (tasks[0].id_task, dt(5, 15)),  # selesai → tetap ikut (tetap memakai slot)
        (tasks[1].id_task, dt(7, 15)),  # terjadwal; sesi `dilewati` di 6/10 tidak ikut
    ]


def test_ke_session_maps_status_to_done(db, user_lengkap):
    user, tasks = user_lengkap
    sessions = [ke_session(r) for r in sesi_user(db, user, *MINGGU_INI)]
    assert [(s.task_number, s.done) for s in sessions] == [(tasks[0].id_task, True), (tasks[1].id_task, False)]


def test_muat_konteks_slot_luang_excludes_routines_and_agenda(db, user_lengkap, monkeypatch):
    monkeypatch.setattr(jadwal_service.settings, "JAM_AKTIF_MULAI", time(8))
    monkeypatch.setattr(jadwal_service.settings, "JAM_AKTIF_SELESAI", time(21))
    user, _ = user_lengkap
    konteks = muat_konteks(db, user, *MINGGU_INI)

    senin = [s for s in konteks.slot_luang if s.start.date() == dt(5, 0).date()]
    selasa = [s for s in konteks.slot_luang if s.start.date() == dt(6, 0).date()]
    rabu = [s for s in konteks.slot_luang if s.start.date() == dt(7, 0).date()]
    assert senin == [Interval(dt(5, 15), dt(5, 21))]                               # kuliah 8-15
    assert selasa == [Interval(dt(6, 8), dt(6, 19))]                               # rapat 19-21
    assert rabu == [Interval(dt(7, 8), dt(7, 16)), Interval(dt(7, 18), dt(7, 21))]  # gym 16-18
    # sesi task sengaja BELUM dikurangkan dari slot_luang
    assert any(s.start <= dt(7, 15) and dt(7, 16) <= s.end for s in rabu)


def test_muat_konteks_blok_sibuk_has_all_sources(db, user_lengkap):
    user, _ = user_lengkap
    blok = muat_konteks(db, user, *MINGGU_INI).blok_sibuk()
    assert sorted({b.kind for b in blok}) == ["agenda", "rutin", "task"]
    assert {b.label for b in blok if b.kind == "rutin"} == {"Kuliah", "Gym"}
    assert "Agenda Akio" not in {b.label for b in blok}


def test_muat_konteks_empty_user(db):
    user, _ = buat_user(db, email="kosong@example.com")
    konteks = muat_konteks(db, user, *MINGGU_INI)
    assert konteks.rutin == [] and konteks.agenda == [] and konteks.sesi == []
    assert len(konteks.slot_luang) == 7  # satu slot jam aktif per hari
