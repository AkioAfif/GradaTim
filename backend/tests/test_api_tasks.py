"""Tes API task: /api/v1/tasks — daftar, filter, detail, ubah status (FR-10)."""

from datetime import datetime
from typing import get_args

import pytest
from sqlalchemy import select

from app.core.status import TASK_STATUSES
from app.models.goal import Goal
from app.models.jadwal_task import JadwalTask
from app.models.milestone import Milestone
from app.models.task import Task
from app.models.task_dependency import TaskDependency
from app.models.user import User
from app.schemas.task import TaskStatus

URL = "/api/v1/tasks"


def _pohon(db, email: str, judul: str, tasks: list[tuple[str, datetime | None, str]]) -> dict[str, int]:
    """Buat goal → milestone → task langsung lewat ORM. Kembalikan {nama_task: id_task} + id_goal."""
    user = db.scalar(select(User).where(User.email == email))
    goal = Goal(user=user, judul_goal=judul, deadline=datetime(2026, 12, 31, 23, 59))
    milestone = Milestone(goal=goal, judul_milestone=f"M {judul}", urutan=1)
    db.add_all([goal, milestone])
    objek = []
    for nama, deadline, status in tasks:
        task = Task(milestone=milestone, nama_task=nama, deadline=deadline, status=status)
        db.add(task)
        objek.append(task)
    db.commit()
    hasil = {t.nama_task: t.id_task for t in objek}
    hasil["id_goal"] = goal.id_goal
    return hasil


@pytest.fixture
def dua_user(client, db, auth_headers):
    a = auth_headers(email="a@contoh.com")
    b = auth_headers(email="b@contoh.com")
    goal1 = _pohon(db, "a@contoh.com", "Goal 1", [
        ("A3", datetime(2026, 10, 9, 23, 59), "todo"),
        ("A1", datetime(2026, 10, 5, 23, 59), "done"),
        ("A2", datetime(2026, 10, 7, 23, 59), "in_progress"),
        ("A-tanpa-deadline", None, "todo"),
    ])
    goal2 = _pohon(db, "a@contoh.com", "Goal 2", [
        ("A1b", datetime(2026, 10, 5, 23, 59), "todo"),  # deadline sama dengan A1 → urut id_task
    ])
    goal_b = _pohon(db, "b@contoh.com", "Goal B", [("B1", datetime(2026, 10, 6, 23, 59), "todo")])
    db.add(TaskDependency(id_task=goal1["A2"], id_task_prasyarat=goal1["A1"]))
    db.commit()
    return {"a": a, "b": b, "goal1": goal1, "goal2": goal2, "goal_b": goal_b}


def _nama(client, headers, **params):
    r = client.get(URL, params=params, headers=headers)
    assert r.status_code == 200, r.text
    return [t["nama_task"] for t in r.json()]


def test_literal_status_sama_dengan_konstanta():
    assert set(get_args(TaskStatus)) == set(TASK_STATUSES)


def test_list_urut_deadline_lalu_id(client, dua_user):
    assert _nama(client, dua_user["a"]) == ["A1", "A1b", "A2", "A3", "A-tanpa-deadline"]


def test_list_berisi_semua_field(client, dua_user):
    a2 = next(t for t in client.get(URL, headers=dua_user["a"]).json() if t["nama_task"] == "A2")
    assert a2 == {
        "id_task": dua_user["goal1"]["A2"],
        "id_milestone": a2["id_milestone"],
        "id_parent_task": None,
        "nama_task": "A2",
        "deskripsi": None,
        "deadline": "2026-10-07T23:59:00",
        "durasi_estimasi": None,
        "status": "in_progress",
        "tingkat_effort": None,
        "tingkat_impact": None,
        "prasyarat": [dua_user["goal1"]["A1"]],
    }


def test_filter_goal(client, dua_user):
    assert _nama(client, dua_user["a"], id_goal=dua_user["goal2"]["id_goal"]) == ["A1b"]


def test_filter_status(client, dua_user):
    assert _nama(client, dua_user["a"], status="todo") == ["A1b", "A3", "A-tanpa-deadline"]
    assert _nama(client, dua_user["a"], status="done") == ["A1"]


def test_filter_goal_dan_status(client, dua_user):
    assert _nama(client, dua_user["a"], id_goal=dua_user["goal1"]["id_goal"], status="todo") == [
        "A3", "A-tanpa-deadline",
    ]


def test_filter_goal_tidak_dikenal_atau_milik_user_lain_list_kosong(client, dua_user):
    assert _nama(client, dua_user["a"], id_goal=9999) == []
    assert _nama(client, dua_user["a"], id_goal=dua_user["goal_b"]["id_goal"]) == []


def test_filter_status_tidak_valid_422(client, dua_user):
    assert client.get(URL, params={"status": "pending"}, headers=dua_user["a"]).status_code == 422


def test_list_hanya_task_milik_sendiri(client, dua_user):
    assert _nama(client, dua_user["b"]) == ["B1"]


def test_get_task(client, dua_user):
    id_a1 = dua_user["goal1"]["A1"]
    r = client.get(f"{URL}/{id_a1}", headers=dua_user["a"])
    assert r.status_code == 200
    assert r.json()["nama_task"] == "A1"
    assert r.json()["status"] == "done"


@pytest.mark.parametrize("status_baru", ["todo", "in_progress", "done"])
def test_patch_setiap_status_valid(client, db, dua_user, status_baru):
    id_a3 = dua_user["goal1"]["A3"]
    r = client.patch(f"{URL}/{id_a3}", json={"status": status_baru}, headers=dua_user["a"])
    assert r.status_code == 200
    assert r.json()["status"] == status_baru
    assert r.json()["nama_task"] == "A3"
    db.expire_all()
    assert db.get(Task, id_a3).status == status_baru


@pytest.mark.parametrize("body", [{"status": "pending"}, {"status": "DONE"}, {"status": None}, {}])
def test_patch_status_tidak_valid_422(client, dua_user, body):
    r = client.patch(f"{URL}/{dua_user['goal1']['A3']}", json=body, headers=dua_user["a"])
    assert r.status_code == 422


def test_patch_tidak_menyentuh_jadwal_task(client, db, dua_user):
    id_a3 = dua_user["goal1"]["A3"]
    db.add(JadwalTask(id_task=id_a3, waktu_mulai=datetime(2026, 10, 8, 9), waktu_selesai=datetime(2026, 10, 8, 10)))
    db.commit()
    client.patch(f"{URL}/{id_a3}", json={"status": "done"}, headers=dua_user["a"])
    db.expire_all()
    assert [j.status for j in db.scalars(select(JadwalTask))] == ["terjadwal"]


def test_task_user_lain_404(client, dua_user):
    id_b1 = dua_user["goal_b"]["B1"]
    assert client.get(f"{URL}/{id_b1}", headers=dua_user["a"]).status_code == 404
    assert client.patch(f"{URL}/{id_b1}", json={"status": "done"}, headers=dua_user["a"]).status_code == 404
    # task B tidak berubah
    assert client.get(f"{URL}/{id_b1}", headers=dua_user["b"]).json()["status"] == "todo"


def test_task_tidak_ada_404(client, dua_user):
    assert client.get(f"{URL}/9999", headers=dua_user["a"]).status_code == 404
    assert client.patch(f"{URL}/9999", json={"status": "done"}, headers=dua_user["a"]).status_code == 404


@pytest.mark.parametrize("method, path", [("get", URL), ("get", f"{URL}/1"), ("patch", f"{URL}/1")])
def test_tanpa_token_401(client, method, path):
    kwargs = {"json": {"status": "done"}} if method == "patch" else {}
    assert getattr(client, method)(path, **kwargs).status_code == 401


def test_task_baru_default_todo(db, dua_user):
    milestone = db.scalar(select(Milestone).limit(1))
    task = Task(milestone=milestone, nama_task="Default")
    db.add(task)
    db.commit()
    assert task.status == "todo"
