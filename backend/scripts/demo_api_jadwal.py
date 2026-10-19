"""
demo_api_jadwal.py — Demo endpoint API kalender & penjadwalan lewat Swagger (untuk laporan / bukti pekerjaan)

Script ini:
    1. Membuat database SQLite demo TERPISAH di folder temp (database tim di .env tidak disentuh)
    2. Mengisi data contoh untuk minggu ini: user demo, kegiatan rutin, agenda, 2 goal + task,
       satu sesi yang sudah terlewat (untuk demo susun ulang), dan goal ketiga dengan 3 sesi
       malam ini (untuk demo kuesioner mood)
    3. Mencetak token login, lalu menjalankan server di http://127.0.0.1:8000/docs

Data dibuat ulang setiap kali script dijalankan, jadi demo bisa diulang dari awal.

Cara pakai (dari folder backend/, venv aktif):
    python scripts/demo_api_jadwal.py

Lalu di http://127.0.0.1:8000/docs:
    1. Klik "Authorize", tempel token yang dicetak, klik Authorize
    2. POST /api/v1/jadwal/goal/{id_goal}   → jadwalkan goal "Belajar Docker" (id dicetak di console)
    3. GET  /api/v1/jadwal                  → isi kalender minggu ini
    4. PATCH /api/v1/jadwal/sesi/{id_jadwal} → pindah sesi ke jam kegiatan rutin → 409 bentrok
    5. POST /api/v1/jadwal/susun-ulang      → sesi terlewat dipindah
    6. POST /api/v1/mood                    → isi semua jawaban 1 (mood LOW) → lihat `rekomendasi`
    7. POST /api/v1/jadwal/susun-ulang      → body {"ditunda": [id_task dari `disarankan_ditunda`]}
    8. GET  /api/v1/mood/hari-ini           → `disarankan_ditunda` sekarang kosong

Langkah 6–8 paling rapi jika demo dijalankan sebelum jam 19:00 (sesi mood dibuat pukul 19:00–21:00 hari ini).
"""

import os
import sys
import tempfile
from datetime import datetime, time, timedelta
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))
sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)  # token langsung tampil sebelum server jalan

# harus sebelum import app: variabel environment mengalahkan nilai DATABASE_URL di .env
DEMO_DB = Path(tempfile.gettempdir()) / "gradatim_demo_api.db"
os.environ["DATABASE_URL"] = f"sqlite:///{DEMO_DB.as_posix()}"

import uvicorn  # noqa: E402

import app.models  # noqa: E402,F401 — daftarkan semua tabel ke Base.metadata
from app.core.security import create_access_token, hash_password  # noqa: E402
from app.core.status import JADWAL_TERJADWAL  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402
from app.main import app as fastapi_app  # noqa: E402
from app.models import Agenda, Goal, JadwalTask, Milestone, Task, TaskDependency, TimeConstraint, User  # noqa: E402
from app.services.jadwal_service import awal_minggu  # noqa: E402

EMAIL, PASSWORD = "demo@gradatim.id", "demo12345"
SEN, SEL, RAB, KAM, JUM, SAB, MIN = range(7)


def isi_data_demo(db, sekarang: datetime) -> tuple[User, Goal, Goal, Goal]:
    user = User(nama="Argya (demo)", email=EMAIL, password=hash_password(PASSWORD))
    db.add(user)
    db.add_all([
        TimeConstraint(user=user, nama="Kuliah", hari_dalam_minggu=hari, waktu_mulai=time(8), waktu_selesai=time(15))
        for hari in (SEN, SEL, RAB, KAM, JUM)
    ])
    db.add_all([
        TimeConstraint(user=user, nama="Gym", hari_dalam_minggu=hari, waktu_mulai=time(16), waktu_selesai=time(18))
        for hari in (SEL, KAM)
    ])
    besok = sekarang.date() + timedelta(days=1)
    db.add(Agenda(user=user, nama="Rapat himpunan",
                  waktu_mulai=datetime.combine(besok, time(19)), waktu_selesai=datetime.combine(besok, time(21))))

    # goal yang akan dijadwalkan lewat endpoint (belum punya sesi)
    docker = Goal(user=user, judul_goal="Belajar Docker")
    m_docker = Milestone(goal=docker, judul_milestone="Minggu 1: dasar Docker", tipe="mingguan")
    tasks = [
        Task(milestone=m_docker, nama_task="Install Docker & hello-world", durasi_estimasi=30),
        Task(milestone=m_docker, nama_task="Pelajari image vs container", durasi_estimasi=60),
        Task(milestone=m_docker, nama_task="Tulis Dockerfile pertama", durasi_estimasi=90),
        Task(milestone=m_docker, nama_task="Coba docker compose", durasi_estimasi=60),
    ]
    db.add_all([docker, m_docker, *tasks])
    db.add_all([TaskDependency(task=tasks[i + 1], task_prasyarat=tasks[i]) for i in range(3)])

    # goal lain yang sudah punya sesi terlewat (masih `terjadwal`) → untuk demo susun ulang
    git = Goal(user=user, judul_goal="Belajar Git")
    m_git = Milestone(goal=git, judul_milestone="Minggu 1: dasar Git", tipe="mingguan")
    t_git = Task(milestone=m_git, nama_task="Latihan commit & branch", durasi_estimasi=60)
    db.add_all([git, m_git, t_git])
    lalu = max((sekarang - timedelta(hours=3)).replace(minute=0, second=0, microsecond=0), awal_minggu(sekarang))
    db.add(JadwalTask(task=t_git, waktu_mulai=lalu, waktu_selesai=lalu + timedelta(hours=1), status=JADWAL_TERJADWAL))

    # goal dengan 3 sesi malam ini, effort/impact berbeda → untuk demo rekomendasi mood
    python = Goal(user=user, judul_goal="Belajar Python")
    m_python = Milestone(goal=python, judul_milestone="Minggu 1: dasar Python", tipe="mingguan")
    db.add_all([python, m_python])
    for i, (nama, effort, impact) in enumerate([
        ("Baca materi list & dict", "low", "high"),
        ("Kerjakan 10 soal latihan", "high", "low"),
        ("Rangkum catatan", "medium", "medium"),
    ]):
        t = Task(milestone=m_python, nama_task=nama, durasi_estimasi=30, tingkat_effort=effort, tingkat_impact=impact)
        mulai = datetime.combine(sekarang.date(), time(19)) + timedelta(minutes=40 * i)
        db.add_all([t, JadwalTask(task=t, waktu_mulai=mulai, waktu_selesai=mulai + timedelta(minutes=30),
                                  status=JADWAL_TERJADWAL)])

    db.commit()
    return user, docker, git, python


def main():
    if DEMO_DB.exists():
        DEMO_DB.unlink()
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        user, docker, git, python = isi_data_demo(db, datetime.now())
        token = create_access_token(user.id_user)
        id_docker, id_git, id_python = docker.id_goal, git.id_goal, python.id_goal

    print("=" * 70)
    print("DEMO API KALENDER GRADATIM")
    print(f"Database demo : {DEMO_DB}")
    print(f"Login         : {EMAIL} / {PASSWORD}")
    print(f"Goal          : Belajar Docker → id_goal = {id_docker}   (belum dijadwalkan)")
    print(f"                Belajar Git    → id_goal = {id_git}   (punya 1 sesi terlewat)")
    print(f"                Belajar Python → id_goal = {id_python}   (3 sesi malam ini, untuk demo mood)")
    print("\nToken (klik 'Authorize' di /docs lalu tempel ini):\n")
    print(token)
    print("\nBuka: http://127.0.0.1:8000/docs   (Ctrl+C untuk berhenti)")
    print("=" * 70)
    uvicorn.run(fastapi_app, host="127.0.0.1", port=8000)


if __name__ == "__main__":
    main()
