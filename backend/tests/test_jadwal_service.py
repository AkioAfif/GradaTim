"""Unit tests untuk app/services/jadwal_service.py (database SQLite in-memory)"""

from datetime import datetime, time

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401 — daftarkan semua tabel ke Base.metadata
from app.core.status import JADWAL_DILEWATI, JADWAL_SELESAI, JADWAL_TERJADWAL, MILESTONE_TIPE_MINGGUAN, TASK_DONE
from app.db.base import Base
from app.models import Agenda, Goal, JadwalTask, Milestone, Task, TaskDependency, TimeConstraint, User
from app.services import jadwal_service
from app.services.kalender_service import kegiatan_rutin_user
from app.services.jadwal_service import (
    DEFAULT_DURASI_MENIT,
    agenda_user,
    awal_minggu,
    cek_bentrok,
    jam_aktif,
    jadwalkan_goal,
    ke_session,
    minggu_sudah_tiba,
    muat_konteks,
    sesi_user,
    susun_ulang_minggu_ini,
)
from app.services.scheduler import Interval, validate_schedule

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
        JadwalTask(task=tasks[0], waktu_mulai=dt(5, 15), waktu_selesai=dt(5, 16), status=JADWAL_SELESAI),
        JadwalTask(task=tasks[1], waktu_mulai=dt(6, 15), waktu_selesai=dt(6, 16), status=JADWAL_DILEWATI),
        JadwalTask(task=tasks[1], waktu_mulai=dt(7, 15), waktu_selesai=dt(7, 16), status=JADWAL_TERJADWAL),
        JadwalTask(task=tasks[2], waktu_mulai=dt(14, 15), waktu_selesai=dt(14, 16), status=JADWAL_TERJADWAL),
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
    rutin = kegiatan_rutin_user(db, user)
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


# ------------------------------------------------------------
# PENJADWALAN GOAL (FR-4)
# ------------------------------------------------------------

SENIN_PAGI = dt(5, 8)


@pytest.fixture
def jam_8_21(monkeypatch):
    monkeypatch.setattr(jadwal_service.settings, "JAM_AKTIF_MULAI", time(8))
    monkeypatch.setattr(jadwal_service.settings, "JAM_AKTIF_SELESAI", time(21))


def buat_goal(db, user, durasi, deadline=None):
    """Goal baru milik `user` dengan satu task per nilai `durasi` (menit, None = tanpa estimasi)."""
    goal = Goal(user=user, judul_goal="Belajar Git", deadline=deadline)
    milestone = Milestone(goal=goal, judul_milestone="Minggu 1")
    tasks = [Task(milestone=milestone, nama_task=f"Git {i}", durasi_estimasi=d) for i, d in enumerate(durasi)]
    db.add_all([goal, milestone, *tasks])
    db.flush()
    return goal, tasks


def sesi_tersimpan(db, task):
    return db.query(JadwalTask).filter_by(id_task=task.id_task).order_by(JadwalTask.waktu_mulai).all()


def test_jadwalkan_goal_saves_sessions_within_week(db, user_lengkap, jam_8_21):
    user, _ = user_lengkap
    goal, tasks = buat_goal(db, user, [60, 90, 45])

    hasil = jadwalkan_goal(db, user, goal, SENIN_PAGI)

    assert hasil.tidak_muat == []
    assert {s.id_task for s in hasil.sesi_baru} == {t.id_task for t in tasks}
    for s in hasil.sesi_baru:
        assert s.id_jadwal is not None and s.status == JADWAL_TERJADWAL
        assert SENIN_PAGI <= s.waktu_mulai and s.waktu_selesai <= MINGGU_INI[1]
    for t in tasks:
        assert sum((s.waktu_selesai - s.waktu_mulai).seconds // 60 for s in sesi_tersimpan(db, t)) == t.durasi_estimasi


def test_jadwalkan_goal_no_conflict_with_routines_agenda_and_other_sessions(db, user_lengkap, jam_8_21):
    user, _ = user_lengkap
    goal, _ = buat_goal(db, user, [120] * 8)

    jadwalkan_goal(db, user, goal, SENIN_PAGI)

    konteks = muat_konteks(db, user, *MINGGU_INI)  # sudah memuat sesi baru
    assert validate_schedule(konteks.sessions, [b for b in konteks.blok_sibuk() if b.kind != "task"]) == []


def test_jadwalkan_goal_skips_done_scheduled_and_parent_tasks(db, jam_8_21):
    user, _ = buat_user(db)
    goal, (selesai, terjadwal, dilewati, induk, anak) = buat_goal(db, user, [60] * 5)
    selesai.status = TASK_DONE
    anak.parent_task = induk
    db.add_all([
        JadwalTask(task=terjadwal, waktu_mulai=dt(14, 9), waktu_selesai=dt(14, 10), status=JADWAL_TERJADWAL),
        JadwalTask(task=dilewati, waktu_mulai=dt(2, 9), waktu_selesai=dt(2, 10), status=JADWAL_DILEWATI),
    ])
    db.flush()

    hasil = jadwalkan_goal(db, user, goal, SENIN_PAGI)

    # task yang sesinya hanya `dilewati` dianggap belum terjadwal; induk diwakili sub-task-nya
    assert {s.id_task for s in hasil.sesi_baru} == {dilewati.id_task, anak.id_task}


def test_jadwalkan_goal_orders_by_milestone_then_id(db, jam_8_21):
    user, _ = buat_user(db)
    goal = Goal(user=user, judul_goal="Belajar Git")
    branching = Milestone(goal=goal, judul_milestone="Branching", urutan=2)
    dasar = Milestone(goal=goal, judul_milestone="Dasar Git", urutan=1)
    task_branching = Task(milestone=branching, nama_task="Merge", durasi_estimasi=780)
    db.add_all([goal, branching, dasar, task_branching])
    db.flush()
    task_dasar = Task(milestone=dasar, nama_task="Commit", durasi_estimasi=780)  # ditambah belakangan
    db.add(task_dasar)
    db.flush()

    jadwalkan_goal(db, user, goal, SENIN_PAGI)

    # tiap task memenuhi satu hari (8-21): milestone urutan 1 dapat Senin walau id_task-nya lebih besar
    assert sesi_tersimpan(db, task_dasar)[0].waktu_mulai < sesi_tersimpan(db, task_branching)[0].waktu_mulai


def test_jadwalkan_goal_orders_nested_milestones_by_path(db, jam_8_21):
    user, _ = buat_user(db)
    goal = Goal(user=user, judul_goal="Belajar Inggris")
    bulan1 = Milestone(goal=goal, judul_milestone="Bulan 1", tipe="bulanan", urutan=0)
    bulan2 = Milestone(goal=goal, judul_milestone="Bulan 2", tipe="bulanan", urutan=1)
    # urutan sub-milestone relatif terhadap induknya: "Bulan 2 › Minggu 1" (urutan 0) tetap setelah
    # "Bulan 1 › Minggu 2" (urutan 1)
    b2m1 = Milestone(goal=goal, parent_milestone=bulan2, judul_milestone="B2 Minggu 1", tipe="mingguan", urutan=0)
    b1m2 = Milestone(goal=goal, parent_milestone=bulan1, judul_milestone="B1 Minggu 2", tipe="mingguan", urutan=1)
    t_b2m1 = Task(milestone=b2m1, nama_task="Reading", durasi_estimasi=780)
    t_b1m2 = Task(milestone=b1m2, nama_task="Tenses", durasi_estimasi=780)
    db.add_all([goal, bulan1, bulan2, b2m1, b1m2, t_b2m1, t_b1m2])
    db.flush()

    jadwalkan_goal(db, user, goal, SENIN_PAGI)

    assert sesi_tersimpan(db, t_b1m2)[0].waktu_mulai < sesi_tersimpan(db, t_b2m1)[0].waktu_mulai


def goal_mingguan(db, user):
    """Goal dengan milestone mingguan minggu lalu, minggu ini (5-11 Okt), dan minggu depan; satu task 60 menit
    per minggu, plus satu task di milestone tanpa deadline."""
    goal = Goal(user=user, judul_goal="Belajar TOEFL")
    tasks = {}
    for nama, deadline in [("lalu", dt(4, 23, 59)), ("ini", dt(11, 23, 59)), ("depan", dt(18, 23, 59)), ("bebas", None)]:
        m = Milestone(goal=goal, judul_milestone=f"Minggu {nama}", tipe=MILESTONE_TIPE_MINGGUAN, deadline=deadline)
        tasks[nama] = Task(milestone=m, nama_task=f"Task {nama}", durasi_estimasi=60)
        db.add_all([m, tasks[nama]])
    db.add(goal)
    db.flush()
    return goal, tasks


def test_minggu_sudah_tiba():
    m = Milestone(judul_milestone="Minggu 3", tipe=MILESTONE_TIPE_MINGGUAN, deadline=dt(18, 23, 59))
    assert not minggu_sudah_tiba(m, dt(11, 23, 59))  # Minggu malam sebelumnya: belum
    assert minggu_sudah_tiba(m, dt(12, 0))  # Senin 00:00 minggunya
    assert minggu_sudah_tiba(m, dt(25, 9))  # sudah lewat: tetap boleh (dikejar)
    # minggu terakhir terpotong deadline goal (Rabu): minggunya tetap mulai Senin
    terakhir = Milestone(judul_milestone="Minggu akhir", tipe=MILESTONE_TIPE_MINGGUAN, deadline=dt(14, 23, 59))
    assert minggu_sudah_tiba(terakhir, dt(12, 8))
    # milestone selain mingguan / tanpa deadline selalu boleh
    assert minggu_sudah_tiba(Milestone(judul_milestone="Bulan", tipe="bulanan", deadline=dt(31, 23, 59)), dt(5, 8))
    assert minggu_sudah_tiba(Milestone(judul_milestone="Manual", deadline=dt(30, 23, 59)), dt(5, 8))


def test_jadwalkan_goal_skips_tasks_of_future_weeks(db, jam_8_21):
    user, _ = buat_user(db)
    goal, tasks = goal_mingguan(db, user)

    hasil = jadwalkan_goal(db, user, goal, SENIN_PAGI)

    assert {s.id_task for s in hasil.sesi_baru} == {tasks[n].id_task for n in ("lalu", "ini", "bebas")}
    assert hasil.tidak_muat == []  # task minggu depan tidak dianggap "tidak muat", hanya belum waktunya
    assert sesi_tersimpan(db, tasks["depan"]) == []


def test_jadwalkan_goal_next_week_tasks_taken_when_week_arrives(db, jam_8_21):
    user, _ = buat_user(db)
    goal, tasks = goal_mingguan(db, user)
    jadwalkan_goal(db, user, goal, SENIN_PAGI)

    hasil = jadwalkan_goal(db, user, goal, dt(12, 8))

    assert [s.id_task for s in hasil.sesi_baru] == [tasks["depan"].id_task]
    assert dt(12, 8) <= hasil.sesi_baru[0].waktu_mulai < dt(19, 0)


def test_jadwalkan_goal_default_duration(db, jam_8_21):
    user, _ = buat_user(db)
    goal, (task,) = buat_goal(db, user, [None])

    hasil = jadwalkan_goal(db, user, goal, SENIN_PAGI)

    assert [(s.waktu_selesai - s.waktu_mulai).seconds // 60 for s in hasil.sesi_baru] == [DEFAULT_DURASI_MENIT]


def test_jadwalkan_goal_respects_dependencies(db, jam_8_21):
    user, _ = buat_user(db)
    goal, (a, b, c) = buat_goal(db, user, [120, 60, 60])
    db.add_all([TaskDependency(task=a, task_prasyarat=c), TaskDependency(task=b, task_prasyarat=a)])
    db.flush()

    jadwalkan_goal(db, user, goal, SENIN_PAGI)

    assert sesi_tersimpan(db, c)[-1].waktu_selesai <= sesi_tersimpan(db, a)[0].waktu_mulai
    assert sesi_tersimpan(db, a)[-1].waktu_selesai <= sesi_tersimpan(db, b)[0].waktu_mulai


def test_jadwalkan_goal_waits_for_already_scheduled_prerequisite(db, jam_8_21):
    user, _ = buat_user(db)
    goal, (prasyarat, task) = buat_goal(db, user, [60, 60])
    db.add_all([
        JadwalTask(task=prasyarat, waktu_mulai=dt(8, 9), waktu_selesai=dt(8, 10), status=JADWAL_TERJADWAL),
        TaskDependency(task=task, task_prasyarat=prasyarat),
    ])
    db.flush()

    hasil = jadwalkan_goal(db, user, goal, SENIN_PAGI)

    assert [s.id_task for s in hasil.sesi_baru] == [task.id_task]
    assert hasil.sesi_baru[0].waktu_mulai >= dt(8, 10)


def test_jadwalkan_goal_prerequisite_scheduled_next_week_means_not_fit(db, jam_8_21):
    user, _ = buat_user(db)
    goal, (prasyarat, task) = buat_goal(db, user, [60, 60])
    db.add_all([
        JadwalTask(task=prasyarat, waktu_mulai=dt(13, 9), waktu_selesai=dt(13, 10), status=JADWAL_TERJADWAL),
        TaskDependency(task=task, task_prasyarat=prasyarat),
    ])
    db.flush()

    hasil = jadwalkan_goal(db, user, goal, SENIN_PAGI)

    assert hasil.sesi_baru == [] and hasil.tidak_muat == [task.id_task]


def test_jadwalkan_goal_counts_existing_load(db, jam_8_21):
    """Hari yang sudah padat oleh goal lain tidak ditambah lagi (beban merata, D5)."""
    user, _ = buat_user(db)
    lain, (sibuk,) = buat_goal(db, user, [480])
    db.add(JadwalTask(task=sibuk, waktu_mulai=dt(5, 9), waktu_selesai=dt(5, 17), status=JADWAL_TERJADWAL))
    goal, _ = buat_goal(db, user, [60, 60])
    db.flush()

    hasil = jadwalkan_goal(db, user, goal, SENIN_PAGI)

    assert all(s.waktu_mulai.date() != dt(5, 0).date() for s in hasil.sesi_baru)


def test_jadwalkan_goal_deadline_limits_range(db, jam_8_21):
    user, _ = buat_user(db)
    goal, (a, b) = buat_goal(db, user, [600, 600], deadline=dt(6, 12))  # Senin 8-21 + Selasa 8-12 = 17 jam

    hasil = jadwalkan_goal(db, user, goal, SENIN_PAGI)

    assert all(s.waktu_selesai <= dt(6, 12) for s in hasil.sesi_baru)
    assert {s.id_task for s in hasil.sesi_baru} == {a.id_task}
    assert hasil.tidak_muat == [b.id_task]


def test_jadwalkan_goal_deadline_passed_saves_nothing(db, jam_8_21):
    user, _ = buat_user(db)
    goal, tasks = buat_goal(db, user, [60, 60], deadline=dt(4, 23))

    hasil = jadwalkan_goal(db, user, goal, SENIN_PAGI)

    assert hasil.sesi_baru == [] and hasil.tidak_muat == [t.id_task for t in tasks]
    assert db.query(JadwalTask).count() == 0


def test_jadwalkan_goal_nothing_to_schedule(db, jam_8_21):
    user, _ = buat_user(db)
    goal, (task,) = buat_goal(db, user, [60])
    task.status = TASK_DONE

    hasil = jadwalkan_goal(db, user, goal, SENIN_PAGI)

    assert hasil.sesi_baru == [] and hasil.tidak_muat == []


def test_jadwalkan_goal_rejects_other_users_goal(db):
    user, _ = buat_user(db)
    lain, _ = buat_user(db, email="akio@example.com")
    goal, _ = buat_goal(db, lain, [60])

    with pytest.raises(ValueError):
        jadwalkan_goal(db, user, goal, SENIN_PAGI)


# ------------------------------------------------------------
# RE-PLANNING (FR-11)
# ------------------------------------------------------------

RABU_SIANG = dt(7, 12)


def sesi(task, mulai, selesai, status=JADWAL_TERJADWAL):
    return JadwalTask(task=task, waktu_mulai=mulai, waktu_selesai=selesai, status=status)


def test_susun_ulang_nothing_missed_changes_nothing(db, jam_8_21):
    user, (a, b, _) = buat_user(db)
    db.add_all([sesi(a, dt(5, 9), dt(5, 10), JADWAL_SELESAI), sesi(b, dt(8, 9), dt(8, 10))])
    db.flush()

    hasil = susun_ulang_minggu_ini(db, user, RABU_SIANG)

    assert hasil == jadwal_service.HasilSusunUlang()
    assert db.query(JadwalTask).count() == 2


def test_susun_ulang_missed_session_kept_as_history_and_rescheduled(db, jam_8_21):
    user, (a, b, _) = buat_user(db)
    terlewat = sesi(a, dt(6, 9), dt(6, 10))
    tetap = sesi(b, dt(8, 9), dt(8, 10))
    db.add_all([terlewat, tetap])
    db.flush()

    hasil = susun_ulang_minggu_ini(db, user, RABU_SIANG)

    assert hasil.dipindah == [a.id_task] and hasil.tidak_muat == []
    assert hasil.sesi_dilewati == [terlewat] and terlewat.status == JADWAL_DILEWATI
    assert [(s.id_task, s.status) for s in hasil.sesi_baru] == [(a.id_task, JADWAL_TERJADWAL)]
    baru = hasil.sesi_baru[0]
    assert baru.id_jadwal is not None
    assert RABU_SIANG <= baru.waktu_mulai and baru.waktu_selesai <= MINGGU_INI[1]
    assert baru.waktu_selesai - baru.waktu_mulai == terlewat.waktu_selesai - terlewat.waktu_mulai
    # sesi lain yang masih valid tidak disentuh
    assert (tetap.waktu_mulai, tetap.status) == (dt(8, 9), JADWAL_TERJADWAL)


def test_susun_ulang_moves_dependent_sessions(db, jam_8_21):
    user, (a, b, _) = buat_user(db)
    db.add_all([
        sesi(a, dt(6, 9), dt(6, 10)),
        sesi(b, dt(7, 13), dt(7, 14)),  # masih valid, tapi bergantung pada a yang dipindah
        TaskDependency(task=b, task_prasyarat=a),
    ])
    db.flush()

    hasil = susun_ulang_minggu_ini(db, user, RABU_SIANG)

    assert hasil.dipindah == sorted([a.id_task, b.id_task])
    assert [s.status for s in sesi_tersimpan(db, a)] == [JADWAL_DILEWATI, JADWAL_TERJADWAL]
    (sesi_b,) = sesi_tersimpan(db, b)  # sesi lama b dihapus, bukan ditandai dilewati
    assert sesi_tersimpan(db, a)[-1].waktu_selesai <= sesi_b.waktu_mulai


def test_susun_ulang_deferred_task_moves_to_tomorrow(db, jam_8_21):
    user, (a, b, _) = buat_user(db)
    db.add_all([sesi(a, dt(7, 15), dt(7, 16)), sesi(b, dt(7, 17), dt(7, 18))])
    db.flush()

    hasil = susun_ulang_minggu_ini(db, user, RABU_SIANG, ditunda=[a.id_task])

    assert hasil.dipindah == [a.id_task] and hasil.sesi_dilewati == []
    (sesi_a,) = sesi_tersimpan(db, a)
    assert sesi_a.waktu_mulai >= dt(8, 0) and sesi_a.status == JADWAL_TERJADWAL
    assert [s.waktu_mulai for s in sesi_tersimpan(db, b)] == [dt(7, 17)]


def test_susun_ulang_ignores_sessions_of_done_tasks(db, jam_8_21):
    user, (a, _, _) = buat_user(db)
    a.status = TASK_DONE  # task ditandai selesai walau sesinya tidak ditandai
    db.add(sesi(a, dt(6, 9), dt(6, 10)))
    db.flush()

    hasil = susun_ulang_minggu_ini(db, user, RABU_SIANG)

    assert hasil.dipindah == [] and hasil.sesi_baru == []
    assert [s.status for s in sesi_tersimpan(db, a)] == [JADWAL_TERJADWAL]


def test_susun_ulang_reports_tasks_that_no_longer_fit(db, jam_8_21):
    user, (a, _, _) = buat_user(db)
    terlewat = sesi(a, dt(10, 9), dt(10, 10))
    db.add(terlewat)
    db.flush()

    hasil = susun_ulang_minggu_ini(db, user, dt(11, 20, 30))  # Minggu 20:30, sisa 30 menit

    assert hasil.tidak_muat == [a.id_task] and hasil.dipindah == [] and hasil.sesi_baru == []
    assert terlewat.status == JADWAL_DILEWATI


def test_susun_ulang_only_touches_own_sessions_and_has_no_conflicts(db, user_lengkap, jam_8_21):
    user, tasks = user_lengkap
    lain = db.query(JadwalTask).join(Task).join(Milestone).join(Goal).filter(Goal.id_user != user.id_user).one()
    db.add(sesi(tasks[2], dt(6, 9), dt(6, 11)))
    db.flush()

    hasil = susun_ulang_minggu_ini(db, user, RABU_SIANG)

    assert hasil.dipindah == [tasks[2].id_task]
    assert (lain.waktu_mulai, lain.status) == (dt(6, 15), JADWAL_TERJADWAL)
    konteks = muat_konteks(db, user, RABU_SIANG, MINGGU_INI[1])
    assert validate_schedule(konteks.sessions, [b for b in konteks.blok_sibuk() if b.kind != "task"]) == []


# ------------------------------------------------------------
# CEK BENTROK (FR-5)
# ------------------------------------------------------------

def test_cek_bentrok_lists_routine_agenda_and_task_by_name(db, user_lengkap):
    user, tasks = user_lengkap
    # Selasa 6/10 14:00-20:00: sesi `dilewati` 15-16 tidak dihitung, rapat himpunan 19-21 dihitung
    bentrok = cek_bentrok(db, user, Interval(dt(6, 14), dt(6, 20)))
    assert [(b.blocking.kind, b.blocking.label, b.overlap) for b in bentrok] == [
        ("agenda", "Rapat himpunan", Interval(dt(6, 19), dt(6, 20))),
    ]
    # Senin 14:00-15:30: kuliah 8-15 dan sesi task 0 (15-16)
    bentrok = cek_bentrok(db, user, Interval(dt(5, 14), dt(5, 15, 30)))
    assert [(b.blocking.kind, b.blocking.label) for b in bentrok] == [("rutin", "Kuliah"), ("task", "Task 0")]


def test_cek_bentrok_ignores_session_being_moved(db, user_lengkap):
    user, _ = user_lengkap
    sesi_rabu = next(s for s in sesi_user(db, user, *MINGGU_INI) if s.waktu_mulai == dt(7, 15))
    geser = Interval(dt(7, 15, 30), dt(7, 16))
    assert [b.blocking.kind for b in cek_bentrok(db, user, geser)] == ["task"]
    assert cek_bentrok(db, user, geser, kecuali_id_jadwal=sesi_rabu.id_jadwal) == []
