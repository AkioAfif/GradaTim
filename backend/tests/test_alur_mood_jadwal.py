"""Alur lengkap FR-6 → FR-7 → FR-11 (D7): isi mood → rekomendasi → tunda sisanya lewat susun ulang."""

from datetime import datetime

from app.api.v1 import jadwal as jadwal_api
from app.core.status import JADWAL_TERJADWAL
from app.models import Goal, JadwalTask, Milestone, Task, TaskDependency, User

SENIN_PAGI = datetime(2026, 10, 5, 7)  # sama dengan conftest.HARI_INI_TES


def bekukan_jam_endpoint_jadwal(monkeypatch, sekarang):
    class JamTetap(datetime):
        @classmethod
        def now(cls, tz=None):
            return sekarang

    monkeypatch.setattr(jadwal_api, "datetime", JamTetap)


def test_mood_low_lalu_tunda_task_yang_disarankan(client, db, auth_headers, hari_ini_beku, monkeypatch):
    bekukan_jam_endpoint_jadwal(monkeypatch, SENIN_PAGI)
    headers = auth_headers(email="alur@contoh.com")
    user = db.query(User).filter_by(email="alur@contoh.com").one()
    milestone = Milestone(goal=Goal(user=user, judul_goal="Belajar Docker"), judul_milestone="M1")
    for jam, (nama, effort, impact) in enumerate(
        [("Ringan penting", "low", "high"), ("Berat", "high", "low"), ("Biasa", "medium", "medium")], start=19
    ):
        t = Task(milestone=milestone, nama_task=nama, tingkat_effort=effort, tingkat_impact=impact,
                 durasi_estimasi=30)
        mulai = datetime(2026, 10, 5, jam)
        db.add(JadwalTask(task=t, waktu_mulai=mulai, waktu_selesai=mulai.replace(minute=30),
                          status=JADWAL_TERJADWAL))
    db.commit()

    # 1. mood LOW → maks 2 task, "Berat" disarankan ditunda
    jawaban = {"q1_focus": 1, "q2_calm": 1, "q3_motivated": 1, "q4_sleep": 1, "q5_readiness": 1}
    rekomendasi = client.post("/api/v1/mood", json=jawaban, headers=headers).json()["rekomendasi"]
    ditunda = [t["id_task"] for t in rekomendasi["disarankan_ditunda"]]
    assert [t["nama_task"] for t in rekomendasi["disarankan_ditunda"]] == ["Berat"]

    # 2. user setuju → frontend mengirim id_task-nya ke susun ulang
    res = client.post("/api/v1/jadwal/susun-ulang", json={"ditunda": ditunda}, headers=headers)
    assert res.status_code == 200, res.text
    body = res.json()
    assert [t["id_task"] for t in body["dipindah"]] == ditunda and body["tidak_muat"] == []
    assert all(s["waktu_mulai"] >= "2026-10-06" for s in body["sesi_baru"])  # mulai besok

    # 3. rekomendasi hari ini tidak lagi menyarankan penundaan; task lain tetap di tempatnya
    sesudah = client.get("/api/v1/mood/hari-ini", headers=headers).json()["rekomendasi"]
    assert sesudah["disarankan_ditunda"] == []
    assert sesudah["direkomendasikan"] == rekomendasi["direkomendasikan"]

    # 4. task yang ditunda tidak hilang: masih ada di kalender minggu ini
    kalender = client.get("/api/v1/jadwal", headers=headers).json()
    sesi_berat = [s for s in kalender["sesi"] if s["id_task"] == ditunda[0]]
    assert len(sesi_berat) == 1 and sesi_berat[0]["waktu_mulai"] >= "2026-10-06"


def test_sesi_prasyarat_ditandai_selesai_membuka_task_lanjutan(client, db, auth_headers, hari_ini_beku, monkeypatch):
    """FR-10 → FR-7: menandai sesi prasyarat `selesai` membuat task-nya `done`, sehingga task lanjutan
    tidak lagi tertahan di rekomendasi mood."""
    bekukan_jam_endpoint_jadwal(monkeypatch, SENIN_PAGI)
    headers = auth_headers(email="alur@contoh.com")
    user = db.query(User).filter_by(email="alur@contoh.com").one()
    milestone = Milestone(goal=Goal(user=user, judul_goal="Belajar Docker"), judul_milestone="M1")
    dasar = Task(milestone=milestone, nama_task="Install Docker", durasi_estimasi=30)
    lanjut = Task(milestone=milestone, nama_task="Tulis Dockerfile", durasi_estimasi=30)
    sesi_dasar = JadwalTask(task=dasar, waktu_mulai=datetime(2026, 10, 5, 8), waktu_selesai=datetime(2026, 10, 5, 8, 30),
                            status=JADWAL_TERJADWAL)
    db.add_all([sesi_dasar, JadwalTask(task=lanjut, waktu_mulai=datetime(2026, 10, 5, 19),
                                       waktu_selesai=datetime(2026, 10, 5, 19, 30), status=JADWAL_TERJADWAL)])
    db.flush()
    db.add(TaskDependency(id_task=lanjut.id_task, id_task_prasyarat=dasar.id_task))
    db.commit()
    jawaban = {"q1_focus": 5, "q2_calm": 5, "q3_motivated": 5, "q4_sleep": 5, "q5_readiness": 5}
    client.post("/api/v1/mood", json=jawaban, headers=headers)

    res = client.patch(f"/api/v1/jadwal/sesi/{sesi_dasar.id_jadwal}", json={"status": "selesai"}, headers=headers)
    assert res.json()["status_task"] == "done"

    rekomendasi = client.get("/api/v1/mood/hari-ini", headers=headers).json()["rekomendasi"]
    assert [t["nama_task"] for t in rekomendasi["direkomendasikan"]] == ["Tulis Dockerfile"]
    assert rekomendasi["disarankan_ditunda"] == []
