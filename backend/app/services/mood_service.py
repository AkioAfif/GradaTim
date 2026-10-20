"""Rekomendasi task hari ini sesuai mood (FR-7, D7)

Kandidat = task yang punya sesi `terjadwal` hari ini. `ai_service.recommend_tasks` memilih yang cocok
dengan kapasitas mood; sisanya disarankan ditunda. Menunda **tidak** dilakukan di sini — user yang
memutuskan, lalu frontend mengirim daftarnya ke `POST /jadwal/susun-ulang {ditunda}` (FR-11).
"""

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.core.status import JADWAL_TERJADWAL, TASK_DONE
from app.models import JadwalTask, Task, User
from app.schemas.mood import MoodAssessment
from app.services import ai_service
from app.services.jadwal_service import prasyarat_task, sesi_user


@dataclass
class TaskHariIni:
    task: Task
    sesi: list[JadwalTask] = field(default_factory=list)  # sesi `terjadwal` hari ini, urut waktu


@dataclass
class RekomendasiHariIni:
    direkomendasikan: list[TaskHariIni] = field(default_factory=list)  # urut prioritas
    disarankan_ditunda: list[TaskHariIni] = field(default_factory=list)  # urut jam sesi pertama


def _task_selesai(db: DbSession, id_tasks: set[int]) -> set[int]:
    """Task berstatus `done` — diisi otomatis dari sesi (`jadwal_service.perbarui_status_task`) atau manual."""
    if not id_tasks:
        return set()
    return set(db.scalars(select(Task.id_task).where(Task.id_task.in_(id_tasks), Task.status == TASK_DONE)))


def _hari_ke(deadline: datetime | None, hari: date) -> int | None:
    """Deadline task → `day_number` relatif hari ini (hari ini = hari ke-1) untuk skor urgensi."""
    return None if deadline is None else (deadline.date() - hari).days + 1


def rekomendasi_hari_ini(db: DbSession, user: User, mood: MoodAssessment, hari: date) -> RekomendasiHariIni:
    awal = datetime.combine(hari, time.min)
    kandidat: dict[int, TaskHariIni] = {}
    for row in sesi_user(db, user, awal, awal + timedelta(days=1)):
        if row.status == JADWAL_TERJADWAL and row.task.status != TASK_DONE:
            kandidat.setdefault(row.id_task, TaskHariIni(row.task)).sesi.append(row)
    if not kandidat:
        return RekomendasiHariIni()

    prasyarat = prasyarat_task(db, list(kandidat))
    selesai = _task_selesai(db, {p for ps in prasyarat.values() for p in ps})
    tasks = [
        {
            "task_number": id_task,
            "effort_level": item.task.tingkat_effort or "medium",
            "impact_level": item.task.tingkat_impact or "medium",
            "day_number": _hari_ke(item.task.deadline, hari),
            # prasyarat yang belum selesai & tidak dijadwalkan hari ini membuat task tidak bisa dipilih
            "depends_on": [p for p in prasyarat.get(id_task, ()) if p not in selesai],
        }
        for id_task, item in kandidat.items()
    ]
    terpilih = [t["task_number"] for t in ai_service.recommend_tasks(tasks, mood, today_day=1)]
    return RekomendasiHariIni(
        direkomendasikan=[kandidat[n] for n in terpilih],
        disarankan_ditunda=[item for n, item in kandidat.items() if n not in terpilih],
    )
