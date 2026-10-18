"""Penghubung database ↔ penjadwal (scheduler.py)

scheduler.py berisi logika murni tanpa database. Modul ini:
    - membaca kegiatan rutin, agenda, dan sesi jadwal user dari database
      lalu mengubahnya ke bentuk yang dipahami scheduler
    - menjadwalkan task sebuah goal dan menyimpan sesinya ke tabel jadwal_task  (FR-4)
    - menyusun ulang jadwal minggu ini: sesi terlewat & task yang ditunda karena mood  (FR-11)
    - mengecek bentrok saat sesi dipindah manual  (FR-5)

Fungsi di sini hanya `flush`, tidak `commit` — commit dilakukan endpoint pemanggil.

Dipanggil dari endpoint API; endpoint tidak perlu tahu detail scheduler.
Keputusan desain: docs/KEPUTUSAN_DESAIN_PENJADWALAN.md
"""

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.core.config import settings
from app.core.status import JADWAL_DILEWATI, JADWAL_SELESAI, JADWAL_TERJADWAL, TASK_DONE
from app.models import Agenda, Goal, JadwalTask, Milestone, Task, TaskDependency, User
from app.services.kalender_service import agenda_ke_busy_block, kegiatan_rutin_user
from app.services.scheduler import (
    BusyBlock,
    Conflict,
    Interval,
    Session,
    TaskToSchedule,
    WeeklyWindow,
    busy_blocks,
    find_conflicts,
    free_slots,
    replan,
    schedule_tasks,
    subtract_intervals,
)

# Sesi `dilewati` hanya riwayat — tidak dianggap sibuk & tidak dijadwalkan ulang lagi.
DEFAULT_DURASI_MENIT = 30  # untuk task tanpa durasi_estimasi


def awal_minggu(waktu: datetime) -> datetime:
    """Senin 00:00 dari minggu yang memuat `waktu` (unit perencanaan = minggu, D7/D11)."""
    return datetime.combine(waktu.date() - timedelta(days=waktu.weekday()), time.min)


def jam_aktif() -> list[WeeklyWindow]:
    """Jam aktif harian dari config, sama untuk tiap hari (D10)."""
    return [WeeklyWindow(hari, settings.JAM_AKTIF_MULAI, settings.JAM_AKTIF_SELESAI) for hari in range(7)]


# ============================================================
# BACA DARI DATABASE
# ============================================================

def agenda_user(db: DbSession, user: User, mulai: datetime, akhir: datetime) -> list[BusyBlock]:
    """Agenda sekali-jalan user yang beririsan dengan [mulai, akhir).
    Kegiatan rutin dibaca lewat `kalender_service.kegiatan_rutin_user`."""
    rows = db.scalars(
        select(Agenda).where(
            Agenda.id_user == user.id_user,
            Agenda.waktu_selesai > mulai,
            Agenda.waktu_mulai < akhir,
        )
    ).all()
    return [agenda_ke_busy_block(r) for r in rows]


def sesi_user(db: DbSession, user: User, mulai: datetime, akhir: datetime) -> list[JadwalTask]:
    """Sesi jadwal_task milik user (lewat task → milestone → goal) yang beririsan dengan [mulai, akhir).
    Sesi berstatus `dilewati` tidak ikut (hanya riwayat)."""
    return list(db.scalars(
        select(JadwalTask)
        .join(Task, JadwalTask.id_task == Task.id_task)
        .join(Milestone, Task.id_milestone == Milestone.id_milestone)
        .join(Goal, Milestone.id_goal == Goal.id_goal)
        .where(
            Goal.id_user == user.id_user,
            JadwalTask.status != JADWAL_DILEWATI,
            JadwalTask.waktu_selesai > mulai,
            JadwalTask.waktu_mulai < akhir,
        )
        .order_by(JadwalTask.waktu_mulai)
    ).all())


def ke_session(row: JadwalTask) -> Session:
    """Baris jadwal_task → Session milik scheduler (task_number = id_task)."""
    return Session(row.id_task, Interval(row.waktu_mulai, row.waktu_selesai), done=row.status == JADWAL_SELESAI)


@dataclass
class KonteksJadwal:
    """Semua yang dibutuhkan scheduler untuk satu user di rentang [mulai, akhir)."""

    mulai: datetime
    akhir: datetime
    rutin: list[WeeklyWindow] = field(default_factory=list)
    agenda: list[BusyBlock] = field(default_factory=list)
    sesi: list[JadwalTask] = field(default_factory=list)
    # jam aktif − kegiatan rutin − agenda (sesi task BELUM dikurangkan; replan butuh bentuk ini)
    slot_luang: list[Interval] = field(default_factory=list)

    @property
    def sessions(self) -> list[Session]:
        return [ke_session(r) for r in self.sesi]

    def blok_sibuk(self) -> list[BusyBlock]:
        """Semua jam sibuk (rutin, agenda, sesi task) — untuk cek bentrok FR-5."""
        return busy_blocks(self.mulai, self.akhir, self.rutin, self.agenda, self.sessions)


def muat_konteks(db: DbSession, user: User, mulai: datetime, akhir: datetime) -> KonteksJadwal:
    rutin = kegiatan_rutin_user(db, user)
    agenda = agenda_user(db, user, mulai, akhir)
    return KonteksJadwal(
        mulai=mulai,
        akhir=akhir,
        rutin=rutin,
        agenda=agenda,
        sesi=sesi_user(db, user, mulai, akhir),
        slot_luang=free_slots(jam_aktif(), mulai, akhir, rutin, busy=[a.interval for a in agenda]),
    )


# ============================================================
# PENJADWALAN GOAL (FR-4)
# ============================================================

@dataclass
class HasilPenjadwalan:
    sesi_baru: list[JadwalTask] = field(default_factory=list)  # baris jadwal_task yang baru dibuat
    tidak_muat: list[int] = field(default_factory=list)  # id_task yang tidak muat sebelum batas waktu


def _urutan_milestone(milestone: Milestone) -> tuple[tuple[int, int], ...]:
    """Kunci urut milestone bertingkat: (urutan, id) dari milestone teratas sampai milestone ini,
    sehingga "Bulan 1 › Minggu 2" berada sebelum "Bulan 2 › Minggu 1"."""
    jalur = []
    while milestone is not None:
        jalur.append((milestone.urutan, milestone.id_milestone))
        milestone = milestone.parent_milestone
    return tuple(reversed(jalur))


def task_belum_terjadwal(db: DbSession, goal: Goal) -> list[Task]:
    """Task goal yang perlu dijadwalkan: belum selesai, tidak punya sub-task (yang dikerjakan
    sub-task-nya), dan belum punya sesi selain yang `dilewati`.
    Diurutkan menurut urutan milestone, lalu id_task — penjadwal memakai urutan ini untuk task
    yang sama-sama siap dikerjakan."""
    tasks = db.scalars(
        select(Task)
        .join(Milestone, Task.id_milestone == Milestone.id_milestone)
        .where(Milestone.id_goal == goal.id_goal, Task.status != TASK_DONE)
        .order_by(Task.id_task)
    ).all()
    punya_sub = set(db.scalars(select(Task.id_parent_task).where(Task.id_parent_task.is_not(None))).all())
    sudah_terjadwal = set(db.scalars(
        select(JadwalTask.id_task).where(
            JadwalTask.id_task.in_([t.id_task for t in tasks]),
            JadwalTask.status != JADWAL_DILEWATI,
        )
    ).all())
    tasks = [t for t in tasks if t.id_task not in punya_sub and t.id_task not in sudah_terjadwal]
    return sorted(tasks, key=lambda t: (_urutan_milestone(t.milestone), t.id_task))


def prasyarat_task(db: DbSession, id_tasks: list[int]) -> dict[int, tuple[int, ...]]:
    """{id_task: (id_task_prasyarat, ...)} dari tabel task_dependency."""
    rows = db.scalars(select(TaskDependency).where(TaskDependency.id_task.in_(id_tasks))).all()
    deps: dict[int, list[int]] = defaultdict(list)
    for r in rows:
        deps[r.id_task].append(r.id_task_prasyarat)
    return {n: tuple(sorted(d)) for n, d in deps.items()}


def _selesai_prasyarat_luar(db: DbSession, id_tasks: set[int]) -> dict[int, datetime]:
    """Waktu selesai sesi terakhir tiap prasyarat yang sudah terjadwal tapi belum selesai."""
    rows = db.execute(
        select(JadwalTask.id_task, JadwalTask.waktu_selesai)
        .join(Task, JadwalTask.id_task == Task.id_task)
        .where(
            JadwalTask.id_task.in_(id_tasks),
            JadwalTask.status != JADWAL_DILEWATI,
            Task.status != TASK_DONE,
        )
    ).all()
    akhir: dict[int, datetime] = {}
    for id_task, selesai in rows:
        akhir[id_task] = max(akhir.get(id_task, selesai), selesai)
    return akhir


def jadwalkan_goal(db: DbSession, user: User, goal: Goal, sekarang: datetime) -> HasilPenjadwalan:
    """
    Jadwalkan task goal yang belum terjadwal ke slot luang minggu ini (FR-4, D5, D7) dan simpan
    sesinya ke jadwal_task berstatus `terjadwal`.

    - Batas waktu: akhir minggu ini (unit perencanaan = minggu, D11), atau deadline goal jika lebih awal.
      Task yang tidak muat masuk `tidak_muat`, tidak pernah dijadwalkan melewati batas itu.
    - Sesi yang sudah ada (goal ini maupun goal lain) dianggap sibuk dan ikut dihitung dalam batas
      beban harian, sehingga hari yang sudah padat tidak ditambah lagi.
    - Task tanpa durasi_estimasi dianggap DEFAULT_DURASI_MENIT.
    - Prasyarat yang sudah terjadwal tapi belum selesai harus ditunggu sampai sesi terakhirnya selesai.
    """
    if goal.id_user != user.id_user:
        raise ValueError("Goal bukan milik user ini")

    tasks = task_belum_terjadwal(db, goal)
    akhir = awal_minggu(sekarang) + timedelta(days=7)
    if goal.deadline is not None:
        akhir = min(akhir, goal.deadline)
    if not tasks:
        return HasilPenjadwalan()
    if akhir <= sekarang:
        return HasilPenjadwalan(tidak_muat=[t.id_task for t in tasks])

    konteks = muat_konteks(db, user, sekarang, akhir)
    sibuk = [s.interval for s in konteks.sessions]
    slot = subtract_intervals(konteks.slot_luang, sibuk)
    beban: dict[date, int] = defaultdict(int)
    for iv in sibuk:
        beban[iv.start.date()] += iv.minutes

    deps = prasyarat_task(db, [t.id_task for t in tasks])
    id_batch = {t.id_task for t in tasks}
    luar = {d for ds in deps.values() for d in ds if d not in id_batch}
    selesai_luar = _selesai_prasyarat_luar(db, luar) if luar else {}

    def paling_awal(id_task: int) -> datetime | None:
        tunggu = [selesai_luar[d] for d in deps.get(id_task, ()) if d in selesai_luar]
        return max(tunggu) if tunggu else None

    hasil = schedule_tasks(
        [
            TaskToSchedule(
                t.id_task,
                t.durasi_estimasi if t.durasi_estimasi and t.durasi_estimasi > 0 else DEFAULT_DURASI_MENIT,
                deps.get(t.id_task, ()),
                paling_awal(t.id_task),
            )
            for t in tasks
        ],
        slot,
        existing_load=beban,
    )

    sesi_baru = [
        JadwalTask(id_task=s.task_number, waktu_mulai=s.interval.start, waktu_selesai=s.interval.end,
                   status=JADWAL_TERJADWAL)
        for s in hasil.sessions
    ]
    db.add_all(sesi_baru)
    db.flush()
    return HasilPenjadwalan(sesi_baru=sesi_baru, tidak_muat=hasil.unscheduled)


# ============================================================
# RE-PLANNING (FR-11)
# ============================================================

@dataclass
class HasilSusunUlang:
    dipindah: list[int] = field(default_factory=list)  # id_task yang sesinya dijadwalkan ulang
    tidak_muat: list[int] = field(default_factory=list)  # tidak muat lagi minggu ini → user memilih konsekuensi (D12)
    sesi_baru: list[JadwalTask] = field(default_factory=list)  # baris jadwal_task pengganti
    sesi_dilewati: list[JadwalTask] = field(default_factory=list)  # sesi terlewat, kini berstatus `dilewati`


def susun_ulang_minggu_ini(
    db: DbSession, user: User, sekarang: datetime, ditunda: Iterable[int] = ()
) -> HasilSusunUlang:
    """
    Jadwalkan ulang sesi minggu ini yang terlewat atau ditunda karena mood (FR-11, D7).

    ditunda: id_task yang hari ini ditunda — sesinya yang belum lewat hari ini dipindah mulai besok.

    Perubahan di tabel jadwal_task:
    - sesi yang terlewat (sudah lewat, masih `terjadwal`) → status `dilewati`, disimpan sebagai riwayat
    - sesi mendatang yang ikut dipindah (ditunda, atau task-nya bergantung pada task yang
      dipindah) → dihapus
    - sesi pengganti → baris baru berstatus `terjadwal`
    Sesi lain yang masih valid tidak disentuh. Sesi dari task yang sudah `done` dianggap selesai.
    """
    mulai = awal_minggu(sekarang)
    konteks = muat_konteks(db, user, mulai, mulai + timedelta(days=7))
    rows = konteks.sesi
    if not rows:
        return HasilSusunUlang()

    def ke_session_replan(row: JadwalTask) -> Session:
        done = row.status == JADWAL_SELESAI or row.task.status == TASK_DONE
        return Session(row.id_task, Interval(row.waktu_mulai, row.waktu_selesai), done=done)

    sessions = [ke_session_replan(r) for r in rows]
    hasil = replan(
        sessions,
        konteks.slot_luang,
        sekarang,
        depends_on=prasyarat_task(db, sorted({r.id_task for r in rows})),
        deferred=ditunda,
    )

    # Sesi lama yang masih ada persis di hasil = tetap; sisanya dipindah. Sesi hasil yang tidak
    # cocok dengan sesi lama mana pun = sesi pengganti.
    sisa = Counter(hasil.sessions)
    dipindah: list[JadwalTask] = []
    for row, sesi in zip(rows, sessions):
        if sisa[sesi] > 0:
            sisa[sesi] -= 1
        else:
            dipindah.append(row)

    sesi_dilewati = []
    for row in dipindah:
        if row.waktu_selesai <= sekarang:
            row.status = JADWAL_DILEWATI
            sesi_dilewati.append(row)
        else:
            db.delete(row)

    sesi_baru = [
        JadwalTask(id_task=s.task_number, waktu_mulai=s.interval.start, waktu_selesai=s.interval.end,
                   status=JADWAL_TERJADWAL)
        for s in sorted(sisa.elements(), key=lambda s: s.interval.start)
    ]
    db.add_all(sesi_baru)
    db.flush()
    return HasilSusunUlang(
        dipindah=hasil.rescheduled,
        tidak_muat=hasil.unscheduled,
        sesi_baru=sesi_baru,
        sesi_dilewati=sesi_dilewati,
    )


# ============================================================
# CEK BENTROK (FR-5)
# ============================================================

def cek_bentrok(db: DbSession, user: User, waktu: Interval, kecuali_id_jadwal: int | None = None) -> list[Conflict]:
    """Bentrok `waktu` dengan kegiatan rutin, agenda, atau sesi task user.

    kecuali_id_jadwal: sesi yang sedang dipindah — tidak dianggap bentrok dengan posisi lamanya.
    Sesi task diberi label nama task-nya, bukan "Task #id".
    """
    konteks = muat_konteks(db, user, waktu.start, waktu.end)
    blok = busy_blocks(waktu.start, waktu.end, konteks.rutin, konteks.agenda)
    blok += [
        BusyBlock(Interval(r.waktu_mulai, r.waktu_selesai), "task", r.task.nama_task)
        for r in konteks.sesi
        if r.id_jadwal != kecuali_id_jadwal
    ]
    return find_conflicts(waktu, blok)
