"""Decomposition & scheduling business logic"""

from datetime import date, datetime, time, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import waktu
from app.core.config import settings
from app.core.status import MILESTONE_TIPE_BULANAN, MILESTONE_TIPE_MINGGUAN, TASK_DONE, TASK_TODO
from app.models.goal import Goal
from app.models.milestone import Milestone
from app.models.task import Task
from app.models.task_dependency import TaskDependency
from app.models.user import User
from app.schemas.ai_decomposition import (
    PlannedTask,
    ProgresTask,
    RencanaGoal,
    RincianMingguRequest,
    TargetMinggu,
)
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


def urutan_milestone(milestone: Milestone) -> tuple[tuple[int, int], ...]:
    """Kunci urut milestone bertingkat: (urutan, id) dari milestone teratas sampai milestone ini.
    Mengurutkan dengan kunci ini = urutan pohon: Bulan 1, Minggu 1, Minggu 2, Bulan 2, Minggu 3, ..."""
    jalur = []
    while milestone is not None:
        jalur.append((milestone.urutan, milestone.id_milestone))
        milestone = milestone.parent_milestone
    return tuple(reversed(jalur))


def simpan_dekomposisi(db: Session, goal: Goal, rencana: RencanaGoal) -> None:
    """Simpan rencana dari AI (D4, D11) sebagai pohon milestone:
    `bulanan` (urutan = bulan_ke) → `mingguan` (urutan = minggu_ke, nomor minggu sepanjang goal) → task.
    Deadline milestone = akhir minggu / bulan terakhirnya; task hanya untuk minggu ke-1.

    Milestone lama goal (beserta task, dependensi, dan jadwalnya) dihapus lalu pohon baru disimpan,
    semuanya dalam satu transaksi. Jika ada error: rollback, lalu error dilempar ulang.
    """
    try:
        goal.milestones.clear()  # delete-orphan: milestone lama → task → task_dependency & jadwal_task
        db.flush()

        minggu_pertama: Milestone | None = None
        for b in rencana.bulan:
            bulanan = Milestone(
                goal=goal,
                judul_milestone=b.judul,
                deskripsi=b.deskripsi or None,
                urutan=b.bulan_ke,
                tipe=MILESTONE_TIPE_BULANAN,
                deadline=waktu.akhir_hari(b.minggu[-1].akhir),
            )
            db.add(bulanan)
            for m in b.minggu:
                mingguan = Milestone(
                    goal=goal,
                    parent_milestone=bulanan,
                    judul_milestone=m.judul,
                    deskripsi=m.deskripsi or None,
                    urutan=m.minggu_ke,
                    tipe=MILESTONE_TIPE_MINGGUAN,
                    deadline=waktu.akhir_hari(m.akhir),
                )
                db.add(mingguan)
                minggu_pertama = minggu_pertama or mingguan

        tambah_task_ai(db, minggu_pertama, rencana.task_minggu_ini)
        db.commit()
    except Exception:
        db.rollback()
        raise


def tambah_task_ai(db: Session, milestone: Milestone, tasks: list[PlannedTask]) -> list[Task]:
    """SATU-SATUNYA tempat yang membaca field task output AI → baris `task` + `task_dependency`.
    Semua task memakai deadline milestone mingguannya. Hanya `flush`; commit oleh pemanggil."""
    task_per_nomor: dict[int, Task] = {}
    baru: list[tuple[Task, list[int]]] = []
    for t in tasks:
        task = Task(
            milestone=milestone,
            nama_task=t.task_title,
            durasi_estimasi=t.estimated_minutes,
            deadline=milestone.deadline,
            tingkat_effort=t.effort_level,
            tingkat_impact=t.impact_level,
            status=TASK_TODO,
        )
        db.add(task)  # SQLAlchemy 2.x tidak meng-cascade objek lewat backref
        task_per_nomor[t.task_number] = task
        baru.append((task, t.depends_on))

    db.flush()  # id_task dibutuhkan untuk baris task_dependency

    for task, nomor_prasyarat in baru:
        sudah: set[int] = set()
        for nomor in nomor_prasyarat:
            prasyarat = task_per_nomor.get(nomor)
            if prasyarat is None or prasyarat is task or prasyarat.id_task in sudah:
                continue  # nomor tidak dikenal, menunjuk diri sendiri, atau duplikat
            sudah.add(prasyarat.id_task)
            db.add(TaskDependency(id_task=task.id_task, id_task_prasyarat=prasyarat.id_task))
    db.flush()
    return [task for task, _ in baru]


# ============================================================
# RINCIAN TASK PER MINGGU (D11)
# ============================================================

def _mingguan(db: Session, goal: Goal) -> list[Milestone]:
    """Milestone mingguan goal, urut minggu ke-1, 2, ... (urutan = nomor minggu sepanjang goal)."""
    return list(db.scalars(
        select(Milestone)
        .where(Milestone.id_goal == goal.id_goal, Milestone.tipe == MILESTONE_TIPE_MINGGUAN)
        .order_by(Milestone.urutan, Milestone.id_milestone)
    ).all())


def milestone_minggu(db: Session, goal: Goal, tanggal: date) -> Milestone | None:
    """Milestone mingguan goal yang minggunya (Senin–Minggu) memuat `tanggal`; None bila tidak ada
    (goal belum direncanakan AI, atau tanggal di luar rentang goal)."""
    senin = datetime.combine(tanggal - timedelta(days=tanggal.weekday()), time.min)
    for m in _mingguan(db, goal):
        if m.deadline is not None and senin <= m.deadline < senin + timedelta(days=7):
            return m
    return None


def _target_minggu(milestone: Milestone) -> TargetMinggu:
    # minggu dibaca dari deadline (= Minggu 23:59, atau deadline goal untuk minggu terakhir). Minggu ke-1
    # aslinya bisa mulai di tengah minggu, tapi yang dirinci lewat sini selalu minggu ke-2 dst.
    akhir = milestone.deadline.date()
    return TargetMinggu(
        minggu_ke=milestone.urutan,
        mulai=akhir - timedelta(days=akhir.weekday()),
        akhir=akhir,
        judul=milestone.judul_milestone,
        deskripsi=milestone.deskripsi or "",
    )


def rincian_minggu_request(
    db: Session, goal: Goal, milestone: Milestone, menit_harian: int | None
) -> RincianMingguRequest:
    """Input `ai_service.rinci_minggu` dari database: target minggu `milestone`, target minggu berikutnya,
    dan progres semua task di minggu-minggu sebelumnya."""
    mingguan = _mingguan(db, goal)
    sebelum = [m for m in mingguan if m.urutan < milestone.urutan]
    berikutnya = next((m for m in mingguan if m.urutan > milestone.urutan), None)
    return RincianMingguRequest(
        judul_goal=goal.judul_goal,
        deskripsi_goal=goal.deskripsi,
        deadline_goal=(goal.deadline or milestone.deadline).date(),
        target=_target_minggu(milestone),
        target_berikutnya=_target_minggu(berikutnya) if berikutnya is not None else None,
        progres=[
            ProgresTask(minggu_ke=m.urutan, judul=t.nama_task, menit=t.durasi_estimasi, selesai=t.status == TASK_DONE)
            for m in sebelum
            for t in sorted(m.tasks, key=lambda t: t.id_task)
        ],
        menit_harian=menit_harian,
    )


def simpan_task_minggu(db: Session, milestone: Milestone, tasks: list[PlannedTask]) -> list[Task]:
    """Simpan task hasil `ai_service.rinci_minggu` ke milestone mingguannya dalam satu transaksi."""
    try:
        baru = tambah_task_ai(db, milestone, tasks)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return baru
