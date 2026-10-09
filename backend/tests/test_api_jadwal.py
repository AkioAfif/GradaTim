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
from app.services import jadwal_service
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


def atur_sekarang(monkeypatch, sekarang):
    """Bekukan datetime.now() di modul endpoint."""

    class JamTetap(datetime):
        @classmethod
        def now(cls, tz=None):
            return sekarang

    monkeypatch.setattr(jadwal_api, "datetime", JamTetap)


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
    atur_sekarang(monkeypatch, dt(14, 10))  # Rabu minggu depan
    body = client.get(URL, headers=auth(user)).json()

    assert body["mulai"] == "2026-10-12T00:00:00"
    assert [a["nama"] for a in body["agenda"]] == ["Agenda minggu depan"]
    assert body["sesi"] == []
    assert [r["nama"] for r in body["kegiatan_rutin"]] == ["Kuliah", "Gym"]  # rutin muncul tiap minggu


def test_lihat_jadwal_invalid_date(client, data):
    user, _, _ = data
    assert client.get(URL, params={"minggu": "bukan-tanggal"}, headers=auth(user)).status_code == 422


# ------------------------------------------------------------
# POST /jadwal/goal/{id_goal}
# ------------------------------------------------------------

@pytest.fixture
def jam_8_21(monkeypatch):
    monkeypatch.setattr(jadwal_service.settings, "JAM_AKTIF_MULAI", time(8))
    monkeypatch.setattr(jadwal_service.settings, "JAM_AKTIF_SELESAI", time(21))


def buat_goal(db, user, durasi, deadline=None):
    goal = Goal(user=user, judul_goal="Belajar Git", deadline=deadline)
    milestone = Milestone(goal=goal, judul_milestone="Minggu 1")
    tasks = [Task(milestone=milestone, nama_task=f"Git {i}", durasi_estimasi=d) for i, d in enumerate(durasi)]
    db.add_all([goal, milestone, *tasks])
    db.commit()
    return goal, tasks


def test_jadwalkan_goal_requires_login(client, data):
    _, goal, _ = data
    assert client.post(f"{URL}/goal/{goal.id_goal}").status_code == 401


def test_jadwalkan_goal_not_found_for_missing_or_other_users_goal(client, db, data):
    user, _, _ = data
    lain = db.query(User).filter_by(email="akio@example.com").one()
    goal_lain, (task_lain,) = buat_goal(db, lain, [60])

    for id_goal in (goal_lain.id_goal, 9999):
        res = client.post(f"{URL}/goal/{id_goal}", headers=auth(user))
        assert res.status_code == 404 and res.json()["detail"] == "Goal tidak ditemukan"
    assert db.query(JadwalTask).filter_by(id_task=task_lain.id_task).count() == 0


def test_jadwalkan_goal_saves_and_shows_in_calendar(client, db, data, jam_8_21, monkeypatch):
    user, _, _ = data
    goal, tasks = buat_goal(db, user, [60, 90])
    atur_sekarang(monkeypatch, dt(7, 12))

    res = client.post(f"{URL}/goal/{goal.id_goal}", headers=auth(user))

    assert res.status_code == 200
    body = res.json()
    assert body["tidak_muat"] == []
    assert {s["id_task"] for s in body["sesi_baru"]} == {t.id_task for t in tasks}
    assert all(s["id_goal"] == goal.id_goal and s["status"] == STATUS_TERJADWAL for s in body["sesi_baru"])
    assert all(s["waktu_mulai"] >= "2026-10-07T12:00:00" for s in body["sesi_baru"])

    # tersimpan (sudah di-commit) dan muncul di kalender
    kalender = client.get(URL, params={"minggu": "2026-10-07"}, headers=auth(user)).json()
    id_kalender = {s["id_jadwal"] for s in kalender["sesi"]}
    assert {s["id_jadwal"] for s in body["sesi_baru"]} <= id_kalender


def test_jadwalkan_goal_twice_does_not_duplicate(client, db, data, jam_8_21, monkeypatch):
    user, _, _ = data
    goal, _ = buat_goal(db, user, [60])
    atur_sekarang(monkeypatch, dt(7, 12))

    pertama = client.post(f"{URL}/goal/{goal.id_goal}", headers=auth(user)).json()
    kedua = client.post(f"{URL}/goal/{goal.id_goal}", headers=auth(user)).json()

    assert len(pertama["sesi_baru"]) == 1
    assert kedua == {"sesi_baru": [], "tidak_muat": []}


def test_jadwalkan_goal_reports_tasks_that_do_not_fit(client, db, data, jam_8_21, monkeypatch):
    user, _, _ = data
    goal, (muat, tidak) = buat_goal(db, user, [60, 600], deadline=dt(7, 15))  # sisa 12:00-15:00
    atur_sekarang(monkeypatch, dt(7, 12))

    body = client.post(f"{URL}/goal/{goal.id_goal}", headers=auth(user)).json()

    assert [s["id_task"] for s in body["sesi_baru"]] == [muat.id_task]
    assert body["tidak_muat"] == [{"id_task": tidak.id_task, "nama_task": "Git 1"}]


# ------------------------------------------------------------
# POST /jadwal/susun-ulang
# ------------------------------------------------------------

def sesi_task(db, task):
    return db.query(JadwalTask).filter_by(id_task=task.id_task).order_by(JadwalTask.waktu_mulai).all()


def test_susun_ulang_requires_login(client):
    assert client.post(f"{URL}/susun-ulang").status_code == 401


def test_susun_ulang_without_body_moves_missed_sessions(client, db, data, jam_8_21, monkeypatch):
    user, _, (_, b) = data  # sesi b Rabu 09:00-10:00 masih `terjadwal`
    atur_sekarang(monkeypatch, dt(7, 12))

    res = client.post(f"{URL}/susun-ulang", headers=auth(user))  # tanpa body

    assert res.status_code == 200
    body = res.json()
    assert body["dipindah"] == [{"id_task": b.id_task, "nama_task": "Task 1"}]
    assert body["tidak_muat"] == []
    assert [(s["status"], s["waktu_mulai"]) for s in body["sesi_dilewati"]] == [
        (STATUS_DILEWATI, "2026-10-07T09:00:00")]
    (baru,) = body["sesi_baru"]
    assert baru["id_task"] == b.id_task and baru["waktu_mulai"] >= "2026-10-07T12:00:00"

    # tersimpan: kalender menampilkan sesi pengganti, bukan sesi yang terlewat
    kalender = client.get(URL, params={"minggu": "2026-10-07"}, headers=auth(user)).json()
    assert [s["id_jadwal"] for s in kalender["sesi"] if s["id_task"] == b.id_task] == [baru["id_jadwal"]]


def test_susun_ulang_deferred_task_moves_to_tomorrow(client, db, data, jam_8_21, monkeypatch):
    user, _, (_, b) = data
    db.add(JadwalTask(task=b, waktu_mulai=dt(7, 19), waktu_selesai=dt(7, 20)))
    db.commit()
    atur_sekarang(monkeypatch, dt(7, 8))  # sebelum sesi 09:00, jadi belum ada yang terlewat

    body = client.post(f"{URL}/susun-ulang", json={"ditunda": [b.id_task]}, headers=auth(user)).json()

    assert [t["id_task"] for t in body["dipindah"]] == [b.id_task]
    assert body["sesi_dilewati"] == []
    assert all(s["waktu_mulai"] >= "2026-10-08T00:00:00" for s in body["sesi_baru"])
    assert all(s.waktu_mulai >= dt(8, 0) for s in sesi_task(db, b) if s.status == STATUS_TERJADWAL)


def test_susun_ulang_rejects_other_users_or_unknown_task(client, db, data, monkeypatch):
    user, _, (_, b) = data
    task_lain = db.query(Task).join(Milestone).join(Goal).join(User).filter(User.email == "akio@example.com").first()
    atur_sekarang(monkeypatch, dt(7, 12))

    for ditunda in ([task_lain.id_task], [b.id_task, 9999]):
        res = client.post(f"{URL}/susun-ulang", json={"ditunda": ditunda}, headers=auth(user))
        assert res.status_code == 404 and res.json()["detail"] == "Task tidak ditemukan"
    # tidak ada yang berubah, termasuk sesi b yang sebenarnya sudah terlewat
    assert [s.status for s in sesi_task(db, b)] == [STATUS_DILEWATI, STATUS_TERJADWAL]


def test_susun_ulang_reports_tasks_that_no_longer_fit(client, db, data, jam_8_21, monkeypatch):
    user, _, (_, b) = data
    atur_sekarang(monkeypatch, dt(11, 20, 30))  # Minggu 20:30, sisa 30 menit

    body = client.post(f"{URL}/susun-ulang", headers=auth(user)).json()

    assert body["tidak_muat"] == [{"id_task": b.id_task, "nama_task": "Task 1"}]
    assert body["dipindah"] == [] and body["sesi_baru"] == []
    assert [s["waktu_mulai"] for s in body["sesi_dilewati"]] == ["2026-10-07T09:00:00"]
