"""Tes ekspor dataset model personalisasi (app/services/dataset_service.py)."""

from datetime import date, datetime

from app.core.status import JADWAL_DILEWATI, JADWAL_SELESAI, JADWAL_TERJADWAL, JADWAL_TIDAK_DIKETAHUI
from app.models import Goal, JadwalTask, Milestone, MoodQuestionnaire, QuestionnaireAnswer, Task, User
from app.services.dataset_service import KOLOM, KOLOM_FITUR, baris_dataset, ringkasan

SAMPAI = datetime(2026, 10, 8, 12)  # Kamis 12:00


def dt(day, hour, minute=0):
    return datetime(2026, 10, day, hour, minute)


def buat_task(db, email):
    user = User(nama=email, email=email, password="x")
    goal = Goal(user=user, judul_goal="Belajar")
    milestone = Milestone(goal=goal, judul_milestone="M1")
    task = Task(milestone=milestone, nama_task="T", durasi_estimasi=60)
    db.add_all([user, goal, milestone, task])
    db.flush()
    return user, task


def sesi(db, task, mulai, status, **kwargs):
    row = JadwalTask(task=task, waktu_mulai=mulai, waktu_selesai=mulai.replace(hour=mulai.hour + 1),
                     status=status, **kwargs)
    db.add(row)
    db.flush()
    return row


def mood(db, user, tanggal, diisi_pada, nilai=(5, 4, 3, 2, 1)):
    db.add(MoodQuestionnaire(
        user=user, tanggal=tanggal, diisi_pada=diisi_pada, hasil_akhir=1,
        answers=[QuestionnaireAnswer(nomor_questionnaire=i, nilai_jawaban=v) for i, v in enumerate(nilai, 1)],
    ))
    db.flush()


FITUR = {"versi": 1, "jam_mulai": 19.0, "hari": 1, "durasi_menit": 60, "effort": "high",
         "tingkat_selesai_riwayat": None}


def test_label_status_dan_penanda(db):
    _, task = buat_task(db, "a@x.com")
    sesi(db, task, dt(6, 9), JADWAL_SELESAI, fitur=FITUR)
    sesi(db, task, dt(6, 13), JADWAL_DILEWATI, eksplorasi=True)
    sesi(db, task, dt(6, 15), JADWAL_TIDAK_DIKETAHUI, dipindah=True)
    sesi(db, task, dt(7, 9), JADWAL_TERJADWAL)  # lewat tapi belum dikonfirmasi
    sesi(db, task, dt(8, 11, 30), JADWAL_SELESAI)  # berakhir 12:30 > SAMPAI → tidak ikut

    baris = baris_dataset(db, SAMPAI)

    assert [(b["status"], b["label"], b["dipindah"], b["eksplorasi"]) for b in baris] == [
        (JADWAL_SELESAI, 1, 0, 0),
        (JADWAL_DILEWATI, 0, 0, 1),
        (JADWAL_TIDAK_DIKETAHUI, None, 1, 0),
        (JADWAL_TERJADWAL, None, 0, 0),
    ]
    assert all(list(b) == KOLOM for b in baris)
    pertama = baris[0]
    assert (pertama["tanggal"], pertama["minggu"]) == ("2026-10-06", "2026-10-05")
    assert (pertama["fitur_versi"], pertama["jam_mulai"], pertama["effort"]) == (1, 19.0, "high")
    assert pertama["sisa_hari_deadline"] is None  # kunci yang tidak ada di snapshot → kosong
    assert all(baris[1][k] is None for k in ["fitur_versi", *KOLOM_FITUR])  # sesi tanpa snapshot


def test_user_disamarkan_menurut_id(db):
    _, task_a = buat_task(db, "a@x.com")
    _, task_b = buat_task(db, "b@x.com")
    sesi(db, task_b, dt(6, 9), JADWAL_SELESAI)
    sesi(db, task_a, dt(6, 10), JADWAL_SELESAI)

    assert [b["user"] for b in baris_dataset(db, SAMPAI)] == ["u02", "u01"]


def test_mood_hanya_bila_diisi_sebelum_sesi_mulai(db):
    user, task = buat_task(db, "a@x.com")
    mood(db, user, date(2026, 10, 6), diisi_pada=dt(6, 8))
    mood(db, user, date(2026, 10, 7), diisi_pada=dt(7, 20))
    mood(db, user, date(2026, 10, 5), diisi_pada=None)  # baris lama tanpa jam
    sesi(db, task, dt(6, 9), JADWAL_SELESAI)   # mood diisi 08:00 → dipakai
    sesi(db, task, dt(6, 8), JADWAL_SELESAI)   # mulai tepat saat mood diisi → dipakai
    sesi(db, task, dt(7, 9), JADWAL_SELESAI)   # mood baru diisi 20:00 → tidak
    sesi(db, task, dt(5, 9), JADWAL_SELESAI)   # jam isi tidak diketahui → tidak

    per_mulai = baris_dataset(db, SAMPAI)  # urut waktu mulai: 5/10 09, 6/10 08, 6/10 09, 7/10 09

    assert [(b["tanggal"], b["mood_diisi"]) for b in per_mulai] == [
        ("2026-10-05", 0), ("2026-10-06", 1), ("2026-10-06", 1), ("2026-10-07", 0)]
    dipakai = per_mulai[1]
    assert [dipakai[k] for k in ("mood_q1_fokus", "mood_q2_tenang", "mood_q3_motivasi",
                                 "mood_q4_tidur", "mood_q5_kesiapan")] == [5, 4, 3, 2, 1]
    assert per_mulai[3]["mood_q1_fokus"] is None


def test_mood_user_lain_tidak_tercampur(db):
    _, task_a = buat_task(db, "a@x.com")
    user_b, _ = buat_task(db, "b@x.com")
    mood(db, user_b, date(2026, 10, 6), diisi_pada=dt(6, 7))
    sesi(db, task_a, dt(6, 9), JADWAL_SELESAI)

    (b,) = baris_dataset(db, SAMPAI)
    assert b["mood_diisi"] == 0


def test_ringkasan(db):
    _, task_a = buat_task(db, "a@x.com")
    _, task_b = buat_task(db, "b@x.com")
    sesi(db, task_a, dt(6, 9), JADWAL_SELESAI, fitur=FITUR, eksplorasi=True)
    sesi(db, task_a, dt(6, 13), JADWAL_DILEWATI, fitur=FITUR)
    sesi(db, task_a, dt(6, 15), JADWAL_TIDAK_DIKETAHUI, fitur=FITUR, dipindah=True)
    sesi(db, task_b, dt(7, 9), JADWAL_TERJADWAL)

    r = ringkasan(baris_dataset(db, SAMPAI))

    assert r == {
        "sesi_berakhir": 4,
        "selesai": 1,
        "dilewati": 1,
        "belum_dikonfirmasi": 2,
        "tingkat_konfirmasi_persen": 50.0,
        "eksplorasi": 1,
        "eksplorasi_persen": 25.0,
        "dipindah": 1,
        "tanpa_snapshot": 1,
        "dengan_mood_persen": 0.0,
        "per_user": {
            "u01": {"sesi_berakhir": 3, "terkonfirmasi": 2, "tingkat_konfirmasi_persen": 66.7},
            "u02": {"sesi_berakhir": 1, "terkonfirmasi": 0, "tingkat_konfirmasi_persen": 0.0},
        },
    }


def test_dataset_kosong(db):
    assert baris_dataset(db, SAMPAI) == []
    r = ringkasan([])
    assert r["sesi_berakhir"] == 0 and r["tingkat_konfirmasi_persen"] is None and r["per_user"] == {}
