"""Unit tests untuk app/services/mood_service.py (rekomendasi task hari ini sesuai mood, FR-7)"""

from datetime import date, datetime

import pytest

from app.core.status import JADWAL_DILEWATI, JADWAL_SELESAI, JADWAL_TERJADWAL, TASK_DONE
from app.models import Goal, JadwalTask, Milestone, Task, TaskDependency, User
from app.schemas.mood import CapacityProbabilities, MoodAssessment
from app.services.mood_service import rekomendasi_hari_ini

HARI = date(2026, 10, 5)  # Senin


def dt(day, hour):
    return datetime(2026, 10, day, hour)


def mood(level, max_tasks):
    return MoodAssessment(
        capacity_level=level, capacity_index=["LOW", "MEDIUM", "HIGH"].index(level), confidence=1.0,
        probabilities=CapacityProbabilities(LOW=0, MEDIUM=0, HIGH=0), max_tasks=max_tasks,
        total_mood_score=15, recommendation_message="",
    )


@pytest.fixture
def milestone(db):
    user = User(nama="Argya", email="argya@example.com", password="hash")
    m = Milestone(goal=Goal(user=user, judul_goal="Belajar Docker"), judul_milestone="M1")
    db.add(m)
    db.flush()
    return m


def task(db, milestone, nama, effort=None, impact=None, deadline=None, status="todo"):
    t = Task(milestone=milestone, nama_task=nama, tingkat_effort=effort, tingkat_impact=impact,
             deadline=deadline, status=status)
    db.add(t)
    db.flush()
    return t


def sesi(db, t, mulai, status=JADWAL_TERJADWAL):
    row = JadwalTask(task=t, waktu_mulai=mulai, waktu_selesai=mulai.replace(minute=30), status=status)
    db.add(row)
    db.flush()
    return row


def nama(items):
    return [i.task.nama_task for i in items]


def test_tanpa_sesi_hari_ini_kosong(db, milestone):
    sesi(db, task(db, milestone, "Besok"), dt(6, 9))
    hasil = rekomendasi_hari_ini(db, milestone.goal.user, mood("HIGH", 6), HARI)
    assert (hasil.direkomendasikan, hasil.disarankan_ditunda) == ([], [])


def test_mood_low_pilih_impact_tinggi_effort_rendah(db, milestone):
    # skor LOW = impact*3 − effort*2
    for jam, (n, effort, impact) in enumerate(
        [("Ringan", "low", "low"), ("Berat penting", "high", "high"), ("Biasa", "medium", "medium"),
         ("Ringan penting", "low", "high")], start=8
    ):
        sesi(db, task(db, milestone, n, effort, impact), dt(5, jam))

    hasil = rekomendasi_hari_ini(db, milestone.goal.user, mood("LOW", 2), HARI)
    assert nama(hasil.direkomendasikan) == ["Ringan penting", "Berat penting"]  # skor 7, 3
    assert nama(hasil.disarankan_ditunda) == ["Ringan", "Biasa"]  # urut jam sesi


def test_mood_high_semua_muat_tidak_ada_yang_ditunda(db, milestone):
    for jam in (8, 9, 10):
        sesi(db, task(db, milestone, f"T{jam}"), dt(5, jam))
    hasil = rekomendasi_hari_ini(db, milestone.goal.user, mood("HIGH", 6), HARI)
    assert len(hasil.direkomendasikan) == 3 and hasil.disarankan_ditunda == []


def test_hanya_sesi_terjadwal_hari_ini_milik_user(db, milestone):
    sesi(db, task(db, milestone, "Kandidat"), dt(5, 8))
    sesi(db, task(db, milestone, "Sesi selesai"), dt(5, 9), JADWAL_SELESAI)
    sesi(db, task(db, milestone, "Sesi dilewati"), dt(5, 10), JADWAL_DILEWATI)
    sesi(db, task(db, milestone, "Task done", status=TASK_DONE), dt(5, 11))
    sesi(db, task(db, milestone, "Kemarin"), dt(4, 11))
    lain = Milestone(goal=Goal(user=User(nama="B", email="b@example.com", password="hash"), judul_goal="G"),
                     judul_milestone="M")
    sesi(db, task(db, lain, "Punya user lain"), dt(5, 12))

    hasil = rekomendasi_hari_ini(db, milestone.goal.user, mood("HIGH", 6), HARI)
    assert nama(hasil.direkomendasikan) == ["Kandidat"] and hasil.disarankan_ditunda == []


def test_dua_sesi_hari_ini_jadi_satu_task(db, milestone):
    t = task(db, milestone, "Panjang")
    pagi, sore = sesi(db, t, dt(5, 8)), sesi(db, t, dt(5, 15))
    hasil = rekomendasi_hari_ini(db, milestone.goal.user, mood("HIGH", 6), HARI)
    assert len(hasil.direkomendasikan) == 1 and hasil.direkomendasikan[0].sesi == [pagi, sore]


def test_deadline_dekat_lebih_diprioritaskan(db, milestone):
    sesi(db, task(db, milestone, "Santai", deadline=dt(30, 23)), dt(5, 8))
    sesi(db, task(db, milestone, "Mepet", deadline=dt(5, 23)), dt(5, 9))
    hasil = rekomendasi_hari_ini(db, milestone.goal.user, mood("MEDIUM", 1), HARI)
    assert nama(hasil.direkomendasikan) == ["Mepet"] and nama(hasil.disarankan_ditunda) == ["Santai"]


def test_prasyarat_hari_ini_dipilih_lebih_dulu(db, milestone):
    dasar = task(db, milestone, "Dasar", "high", "low")  # skor HIGH kecil, tapi prasyarat
    lanjut = task(db, milestone, "Lanjutan", "high", "high")
    db.add(TaskDependency(id_task=lanjut.id_task, id_task_prasyarat=dasar.id_task))
    sesi(db, lanjut, dt(5, 8))
    sesi(db, dasar, dt(5, 9))

    hasil = rekomendasi_hari_ini(db, milestone.goal.user, mood("HIGH", 6), HARI)
    assert nama(hasil.direkomendasikan) == ["Dasar", "Lanjutan"]


def test_prasyarat_belum_selesai_di_luar_hari_ini_task_ditunda(db, milestone):
    dasar = task(db, milestone, "Dasar")
    sesi(db, dasar, dt(2, 9))  # terlewat, belum selesai
    lanjut = task(db, milestone, "Lanjutan")
    db.add(TaskDependency(id_task=lanjut.id_task, id_task_prasyarat=dasar.id_task))
    sesi(db, lanjut, dt(5, 8))

    hasil = rekomendasi_hari_ini(db, milestone.goal.user, mood("HIGH", 6), HARI)
    assert hasil.direkomendasikan == [] and nama(hasil.disarankan_ditunda) == ["Lanjutan"]


@pytest.mark.parametrize("cara_selesai", ["task_done", "semua_sesi_selesai"])
def test_prasyarat_selesai_tidak_menahan(db, milestone, cara_selesai):
    dasar = task(db, milestone, "Dasar", status=TASK_DONE if cara_selesai == "task_done" else "todo")
    sesi(db, dasar, dt(2, 9), JADWAL_SELESAI)
    sesi(db, dasar, dt(3, 9), JADWAL_DILEWATI)  # riwayat dilewati tidak dihitung
    lanjut = task(db, milestone, "Lanjutan")
    db.add(TaskDependency(id_task=lanjut.id_task, id_task_prasyarat=dasar.id_task))
    sesi(db, lanjut, dt(5, 8))

    hasil = rekomendasi_hari_ini(db, milestone.goal.user, mood("HIGH", 6), HARI)
    assert nama(hasil.direkomendasikan) == ["Lanjutan"]


def test_prasyarat_sebagian_sesi_selesai_masih_menahan(db, milestone):
    dasar = task(db, milestone, "Dasar")
    sesi(db, dasar, dt(2, 9), JADWAL_SELESAI)
    sesi(db, dasar, dt(3, 9))  # sesi kedua belum dikerjakan
    lanjut = task(db, milestone, "Lanjutan")
    db.add(TaskDependency(id_task=lanjut.id_task, id_task_prasyarat=dasar.id_task))
    sesi(db, lanjut, dt(5, 8))

    hasil = rekomendasi_hari_ini(db, milestone.goal.user, mood("HIGH", 6), HARI)
    assert nama(hasil.disarankan_ditunda) == ["Lanjutan"]
