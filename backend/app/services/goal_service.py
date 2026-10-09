"""Decomposition & scheduling business logic"""

from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.core import waktu
from app.core.config import settings
from app.core.status import TASK_TODO
from app.models.goal import Goal
from app.models.milestone import Milestone
from app.models.task import Task
from app.models.task_dependency import TaskDependency
from app.models.user import User
from app.schemas.ai_decomposition import GoalDecomposition
from app.services import kalender_service, scheduler

# rentang GoalDecompositionRequest.menit_harian
MENIT_HARIAN_MIN = 15
MENIT_HARIAN_MAKS = 720


class WaktuLuangTidakCukup(Exception):
    """Waktu luang harian (jam aktif − kegiatan rutin) di bawah batas minimum AI decomposer."""


def hitung_menit_harian(db: Session, user: User) -> int:
    """Rata-rata menit luang per hari (D6): jam aktif harian (D10, dari config) − kegiatan rutin user.

    Hasil di atas 720 dipotong ke 720; di bawah 15 → WaktuLuangTidakCukup.
    """
    jam_aktif = [
        scheduler.WeeklyWindow(hari, settings.JAM_AKTIF_MULAI, settings.JAM_AKTIF_SELESAI) for hari in range(7)
    ]
    menit = scheduler.average_daily_minutes(jam_aktif, kalender_service.kegiatan_rutin_user(db, user))
    if menit < MENIT_HARIAN_MIN:
        raise WaktuLuangTidakCukup(f"Waktu luang harian terlalu sedikit (< {MENIT_HARIAN_MIN} menit)")
    return min(menit, MENIT_HARIAN_MAKS)


def simpan_dekomposisi(db: Session, goal: Goal, hasil: GoalDecomposition, today: date) -> None:
    """SATU-SATUNYA tempat yang tahu bentuk output AI.
    Saat output AI berubah ke bulanan → mingguan → task (D11), cukup fungsi ini yang diganti.

    Milestone lama goal (beserta task, dependensi, dan jadwalnya) dihapus lalu pohon baru disimpan,
    semuanya dalam satu transaksi. Jika ada error: rollback, lalu error dilempar ulang.
    `hasil.goal_title` tidak dipakai — judul tetap `goal.judul_goal` dari user.
    """
    try:
        goal.milestones.clear()  # delete-orphan: milestone lama → task → task_dependency & jadwal_task
        db.flush()

        task_per_nomor: dict[int, Task] = {}
        prasyarat_per_task: list[tuple[Task, list[int]]] = []
        for m in hasil.milestones:
            milestone = Milestone(
                goal=goal,
                judul_milestone=m.milestone_title,
                urutan=m.order,
                tipe=None,  # datar dulu; bulanan/mingguan menyusul (D11)
                id_parent_milestone=None,
            )
            db.add(milestone)
            for t in m.tasks:
                task = Task(
                    milestone=milestone,
                    nama_task=t.task_title,
                    durasi_estimasi=t.estimated_minutes,
                    deadline=waktu.akhir_hari(today + timedelta(days=t.day_number - 1)),
                    tingkat_effort=t.effort_level,
                    tingkat_impact=t.impact_level,
                    status=TASK_TODO,
                )
                db.add(task)  # SQLAlchemy 2.x tidak meng-cascade objek lewat backref
                task_per_nomor[t.task_number] = task
                prasyarat_per_task.append((task, t.depends_on))
            milestone.deadline = max((task.deadline for task in milestone.tasks), default=None)

        db.flush()  # id_task dibutuhkan untuk baris task_dependency

        for task, nomor_prasyarat in prasyarat_per_task:
            sudah: set[int] = set()
            for nomor in nomor_prasyarat:
                prasyarat = task_per_nomor.get(nomor)
                if prasyarat is None or prasyarat is task or prasyarat.id_task in sudah:
                    continue  # nomor tidak dikenal, menunjuk diri sendiri, atau duplikat
                sudah.add(prasyarat.id_task)
                db.add(TaskDependency(id_task=task.id_task, id_task_prasyarat=prasyarat.id_task))

        db.commit()
    except Exception:
        db.rollback()
        raise
