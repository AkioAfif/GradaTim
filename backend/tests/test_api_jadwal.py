"""Test endpoint /api/v1/jadwal (database SQLite in-memory, token JWT asli)"""

from datetime import datetime, time

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401 — daftarkan semua tabel ke Base.metadata
from app.api.deps import get_db
from app.api.v1 import jadwal as jadwal_api
from app.core.config import settings
from app.core.security import create_access_token
from app.db.base import Base
from app.main import app as fastapi_app
from app.models import Agenda, Goal, JadwalTask, Milestone, Task, TimeConstraint, User
from app.services.jadwal_service import STATUS_DILEWATI, STATUS_SELESAI, STATUS_TERJADWAL

SEN, RAB = 0, 2
URL = "/api/v1/jadwal"


def dt(day, hour, minute=0):
    return datetime(2026, 10, day, hour, minute)


@pytest.fixture
def db():
    # StaticPool: satu koneksi dipakai bersama, agar data test terlihat dari thread TestClient
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


@pytest.fixture
def client(db):
    fastapi_app.dependency_overrides[get_db] = lambda: db
    yield TestClient(fastapi_app)
    fastapi_app.dependency_overrides.clear()


def buat_user(db, email="argya@example.com"):
    user = User(nama="Argya", email=email, password="hash")
    goal = Goal(user=user, judul_goal="Belajar Docker")
    milestone = Milestone(goal=goal, judul_milestone="Dasar Docker")
    tasks = [Task(milestone=milestone, nama_task=f"Task {i}", durasi_estimasi=60) for i in range(2)]
    db.add_all([user, goal, milestone, *tasks])
    db.commit()
    return user, goal, tasks


def auth(user):
    return {"Authorization": f"Bearer {create_access_token(user.id_user)}"}


@pytest.fixture
def data(db):
    user, goal, (a, b) = buat_user(db)
    db.add_all([
        TimeConstraint(user=user, nama="Kuliah", hari_dalam_minggu=SEN, waktu_mulai=time(8), waktu_selesai=time(15)),
        TimeConstraint(user=user, nama="Gym", hari_dalam_minggu=RAB, waktu_mulai=time(16), waktu_selesai=time(18)),
        Agenda(user=user, nama="Rapat himpunan", waktu_mulai=dt(6, 19), waktu_selesai=dt(6, 21)),
        Agenda(user=user, nama="Agenda minggu depan", waktu_mulai=dt(13, 19), waktu_selesai=dt(13, 21)),
        JadwalTask(task=a, waktu_mulai=dt(5, 15), waktu_selesai=dt(5, 16), status=STATUS_SELESAI),
        JadwalTask(task=b, waktu_mulai=dt(6, 15), waktu_selesai=dt(6, 16), status=STATUS_DILEWATI),
        JadwalTask(task=b, waktu_mulai=dt(7, 9), waktu_selesai=dt(7, 10), status=STATUS_TERJADWAL),
    ])
    lain, _, (tugas_lain, _) = buat_user(db, email="akio@example.com")
    db.add_all([
        Agenda(user=lain, nama="Agenda Akio", waktu_mulai=dt(6, 10), waktu_selesai=dt(6, 11)),
        JadwalTask(task=tugas_lain, waktu_mulai=dt(6, 15), waktu_selesai=dt(6, 16)),
    ])
    db.commit()
    return user, goal, (a, b)


# ------------------------------------------------------------
# GET /jadwal
# ------------------------------------------------------------

def test_lihat_jadwal_requires_login(client):
    assert client.get(URL).status_code == 401


def test_lihat_jadwal_mingguan(client, data):
    user, goal, (a, b) = data
    res = client.get(URL, params={"minggu": "2026-10-07"}, headers=auth(user))  # Rabu → minggu Senin 5 Okt

    assert res.status_code == 200
    body = res.json()
    assert (body["mulai"], body["akhir"]) == ("2026-10-05T00:00:00", "2026-10-12T00:00:00")
    assert body["jam_aktif_mulai"] == settings.JAM_AKTIF_MULAI.isoformat()
    assert body["jam_aktif_selesai"] == settings.JAM_AKTIF_SELESAI.isoformat()
    assert body["kegiatan_rutin"] == [
        {"nama": "Kuliah", "waktu_mulai": "2026-10-05T08:00:00", "waktu_selesai": "2026-10-05T15:00:00"},
        {"nama": "Gym", "waktu_mulai": "2026-10-07T16:00:00", "waktu_selesai": "2026-10-07T18:00:00"},
    ]
    assert body["agenda"] == [
        {"nama": "Rapat himpunan", "waktu_mulai": "2026-10-06T19:00:00", "waktu_selesai": "2026-10-06T21:00:00"},
    ]
    # sesi `dilewati` dan sesi milik user lain tidak ikut
    assert [(s["id_task"], s["status"], s["waktu_mulai"]) for s in body["sesi"]] == [
        (a.id_task, STATUS_SELESAI, "2026-10-05T15:00:00"),
        (b.id_task, STATUS_TERJADWAL, "2026-10-07T09:00:00"),
    ]
    assert body["sesi"][0]["nama_task"] == "Task 0" and body["sesi"][0]["id_goal"] == goal.id_goal
    assert body["sesi"][0]["id_jadwal"] > 0


def test_lihat_jadwal_default_this_week(client, data, monkeypatch):
    user, _, _ = data

    class JamTetap(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 10, 14, 10)  # Rabu minggu depan

    monkeypatch.setattr(jadwal_api, "datetime", JamTetap)
    body = client.get(URL, headers=auth(user)).json()

    assert body["mulai"] == "2026-10-12T00:00:00"
    assert [a["nama"] for a in body["agenda"]] == ["Agenda minggu depan"]
    assert body["sesi"] == []
    assert [r["nama"] for r in body["kegiatan_rutin"]] == ["Kuliah", "Gym"]  # rutin muncul tiap minggu


def test_lihat_jadwal_invalid_date(client, data):
    user, _, _ = data
    assert client.get(URL, params={"minggu": "bukan-tanggal"}, headers=auth(user)).status_code == 422
