"""Scheduling logic — penjadwalan otomatis task ke kalender (FR-4, FR-5, FR-11)

Fungsi murni tanpa database. Keputusan desain: docs/KEPUTUSAN_DESAIN_PENJADWALAN.md

1. free_slots() — slot waktu luang konkret (keputusan D10: jam luang tidak diinput user):
    jam aktif harian
    − kegiatan rutin mingguan (kuliah, gym, ...)
    − jam sibuk lain (agenda sekali-jalan, sesi task yang sudah terjadwal)
    = slot luang yang boleh diisi task

2. schedule_tasks() — menempatkan task ke slot luang (FR-4), merata per hari, boleh dipecah
   ke beberapa sesi, urut sesuai dependensi.

3. find_conflicts() / validate_schedule() — deteksi bentrok jadwal (FR-5), mis. saat user
   memindahkan sesi secara manual.

Semua waktu memakai datetime lokal (WIB) tanpa timezone.
"""

import math
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from typing import Iterable, Optional

MIN_SESSION_MINUTES = 15  # sisa slot di bawah ini tidak dipakai (lihat §7 dokumen desain)
DAILY_CAP_TOLERANCE = 1.2  # batas beban harian = rata-rata × toleransi (D5: merata, tidak dipenuhi)


@dataclass(frozen=True)
class WeeklyWindow:
    """Rentang jam yang berulang tiap minggu — bentuknya sama dengan time_constraint / kegiatan rutin.

    weekday: 0=Senin ... 6=Minggu (sama dengan TimeConstraint.hari_dalam_minggu dan date.weekday()).
    Jika end <= start, rentang dianggap melewati tengah malam (mis. 22:00-01:00).
    label: nama kegiatan (mis. "Kuliah"), dipakai untuk pesan bentrok. Tidak ikut perbandingan.
    """

    weekday: int
    start: time
    end: time
    label: str = field(default="", compare=False)

    def __post_init__(self):
        if not 0 <= self.weekday <= 6:
            raise ValueError(f"weekday harus 0-6, diterima {self.weekday}")
        if self.start == self.end:
            raise ValueError("start dan end tidak boleh sama")

    @property
    def minutes(self) -> int:
        start = datetime.combine(date.min, self.start)
        end = datetime.combine(date.min, self.end)
        if end <= start:
            end += timedelta(days=1)
        return int((end - start).total_seconds() // 60)


@dataclass(frozen=True)
class Interval:
    """Rentang waktu konkret [start, end)."""

    start: datetime
    end: datetime

    def __post_init__(self):
        if self.end <= self.start:
            raise ValueError(f"end ({self.end}) harus setelah start ({self.start})")

    @property
    def minutes(self) -> int:
        return int((self.end - self.start).total_seconds() // 60)


def _expand_weekly_each(
    windows: Iterable[WeeklyWindow], start: datetime, end: datetime
) -> list[tuple[WeeklyWindow, Interval]]:
    """Setiap kemunculan konkret tiap rentang mingguan di [start, end), belum digabung."""
    windows = list(windows)
    occurrences = []
    # mulai sehari sebelumnya agar rentang lewat tengah malam dari hari sebelumnya ikut terhitung
    day = start.date() - timedelta(days=1)
    while day <= end.date():
        for w in windows:
            if day.weekday() != w.weekday:
                continue
            w_start = datetime.combine(day, w.start)
            w_end = w_start + timedelta(minutes=w.minutes)
            clipped_start, clipped_end = max(w_start, start), min(w_end, end)
            if clipped_start < clipped_end:
                occurrences.append((w, Interval(clipped_start, clipped_end)))
        day += timedelta(days=1)
    return occurrences


def expand_weekly(windows: Iterable[WeeklyWindow], start: datetime, end: datetime) -> list[Interval]:
    """Ubah rentang mingguan jadi interval konkret yang beririsan dengan [start, end), lalu gabungkan."""
    return merge_intervals(iv for _, iv in _expand_weekly_each(windows, start, end))


def merge_intervals(intervals: Iterable[Interval]) -> list[Interval]:
    """Urutkan dan gabungkan interval yang tumpang tindih atau bersambung."""
    merged: list[Interval] = []
    for iv in sorted(intervals, key=lambda i: i.start):
        if merged and iv.start <= merged[-1].end:
            last = merged[-1]
            merged[-1] = Interval(last.start, max(last.end, iv.end))
        else:
            merged.append(iv)
    return merged


def subtract_intervals(free: Iterable[Interval], busy: Iterable[Interval]) -> list[Interval]:
    """Kurangi interval `free` dengan semua interval `busy`."""
    busy = merge_intervals(busy)
    result = []
    for f in merge_intervals(free):
        cursor = f.start
        for b in busy:
            if b.end <= cursor or b.start >= f.end:
                continue
            if b.start > cursor:
                result.append(Interval(cursor, b.start))
            cursor = max(cursor, b.end)
            if cursor >= f.end:
                break
        if cursor < f.end:
            result.append(Interval(cursor, f.end))
    return result


def free_slots(
    availability: Iterable[WeeklyWindow],
    start: datetime,
    end: datetime,
    routines: Iterable[WeeklyWindow] = (),
    busy: Iterable[Interval] = (),
    min_minutes: int = MIN_SESSION_MINUTES,
) -> list[Interval]:
    """
    Slot luang konkret di antara [start, end) yang boleh diisi task.

    Args:
        availability: jam yang boleh dipakai (D10: jam aktif harian, bukan input user)
        start: biasanya "sekarang" — slot sebelum ini tidak dipakai
        end: biasanya deadline goal / akhir minggu perencanaan
        routines: kegiatan rutin mingguan (kuliah, gym, ...) → dianggap sibuk
        busy: jam sibuk konkret lain (agenda, sesi task yang sudah terjadwal) → dianggap sibuk
        min_minutes: slot yang lebih pendek dari ini dibuang
    """
    if end <= start:
        return []
    free = expand_weekly(availability, start, end)
    all_busy = expand_weekly(routines, start, end) + list(busy)
    return [s for s in subtract_intervals(free, all_busy) if s.minutes >= min_minutes]


def average_daily_minutes(
    availability: Iterable[WeeklyWindow], routines: Iterable[WeeklyWindow] = ()
) -> int:
    """
    Rata-rata menit luang per hari dalam seminggu (keputusan D6: pengganti input manual `menit_harian`
    untuk AI decomposer). Dihitung dari satu minggu contoh, sudah dikurangi kegiatan rutin.
    """
    week_start = datetime(2024, 1, 1)  # hari Senin; tanggal apa pun boleh, yang penting satu minggu penuh
    slots = free_slots(availability, week_start, week_start + timedelta(days=7), routines, min_minutes=1)
    return sum(s.minutes for s in slots) // 7


# ============================================================
# PENEMPATAN TASK (FR-4)
# ============================================================

@dataclass(frozen=True)
class TaskToSchedule:
    """
    task_number: id task (sama dengan task_number dari AI decomposer)
    minutes: durasi total task
    depends_on: task_number prasyarat. Prasyarat yang tidak ada di daftar yang sedang dijadwalkan
        dianggap sudah selesai (mis. task minggu lalu).
    earliest: task tidak boleh dimulai sebelum waktu ini (mis. dari day_number hasil AI)
    """

    task_number: int
    minutes: int
    depends_on: tuple[int, ...] = ()
    earliest: Optional[datetime] = None


@dataclass(frozen=True)
class Session:
    """Satu sesi kerja; satu task bisa punya beberapa sesi (keputusan D2)."""

    task_number: int
    interval: Interval


@dataclass
class ScheduleResult:
    sessions: list[Session] = field(default_factory=list)
    unscheduled: list[int] = field(default_factory=list)  # task_number yang tidak muat
    daily_cap_minutes: int = 0

    def daily_load(self) -> dict[date, int]:
        load: dict[date, int] = defaultdict(int)
        for s in self.sessions:
            load[s.interval.start.date()] += s.interval.minutes
        return dict(sorted(load.items()))


def _dependency_order(tasks: list[TaskToSchedule]) -> tuple[list[TaskToSchedule], list[int]]:
    """Urutan topologis (prasyarat dulu); seri diurutkan menurut earliest lalu task_number.
    Task yang terlibat dependensi melingkar dikembalikan sebagai daftar kedua."""
    known = {t.task_number for t in tasks}
    pending = {t.task_number: {d for d in t.depends_on if d in known} for t in tasks}
    by_number = {t.task_number: t for t in tasks}
    ordered: list[TaskToSchedule] = []
    while pending:
        ready = [n for n, deps in pending.items() if not deps]
        if not ready:
            break
        ready.sort(key=lambda n: (by_number[n].earliest or datetime.min, n))
        for n in ready:
            ordered.append(by_number[n])
            del pending[n]
        for deps in pending.values():
            deps.difference_update(ready)
    return ordered, sorted(pending)


def _plan_task(
    minutes: int,
    ready_at: datetime,
    free: list[Interval],
    load: dict[date, int],
    daily_cap: int,
    min_session: int,
) -> Optional[list[Interval]]:
    """Cari potongan waktu untuk satu task tanpa mengubah state. None jika tidak muat."""
    remaining = minutes
    pieces: list[Interval] = []
    planned_load: dict[date, int] = defaultdict(int)
    for slot in free:
        if remaining == 0:
            break
        start = max(slot.start, ready_at)
        if start >= slot.end:
            continue
        day = start.date()
        room = min(int((slot.end - start).total_seconds() // 60),
                   daily_cap - load.get(day, 0) - planned_load[day])
        take = min(remaining, room)
        left = remaining - take
        if 0 < left < min_session:
            take = remaining - min_session  # jangan sisakan potongan terlalu kecil untuk sesi berikutnya
        if take <= 0 or (take < min_session and take != remaining):
            continue
        pieces.append(Interval(start, start + timedelta(minutes=take)))
        planned_load[day] += take
        remaining -= take
    return pieces if remaining == 0 else None


def _schedule_with_cap(
    ordered: list[TaskToSchedule], slots: list[Interval], daily_cap: int, min_session: int
) -> ScheduleResult:
    free = list(slots)
    load: dict[date, int] = defaultdict(int)
    finished_at: dict[int, datetime] = {}
    result = ScheduleResult(daily_cap_minutes=daily_cap)
    numbers = {t.task_number for t in ordered}

    for task in ordered:
        deps = [d for d in task.depends_on if d in numbers]
        if any(d not in finished_at for d in deps):  # prasyarat tidak terjadwal → task ini juga tidak
            result.unscheduled.append(task.task_number)
            continue
        ready_at = max([finished_at[d] for d in deps] + [task.earliest or datetime.min])
        pieces = _plan_task(task.minutes, ready_at, free, load, daily_cap, min_session)
        if pieces is None:
            result.unscheduled.append(task.task_number)
            continue
        for p in pieces:
            result.sessions.append(Session(task.task_number, p))
            load[p.start.date()] += p.minutes
        free = subtract_intervals(free, pieces)
        finished_at[task.task_number] = pieces[-1].end

    result.sessions.sort(key=lambda s: s.interval.start)
    return result


def schedule_tasks(
    tasks: Iterable[TaskToSchedule],
    slots: Iterable[Interval],
    min_session: int = MIN_SESSION_MINUTES,
) -> ScheduleResult:
    """
    Tempatkan task ke slot luang (hasil free_slots) secara otomatis — FR-4.

    Aturan:
    - Prasyarat dijadwalkan lebih dulu; task baru mulai setelah sesi terakhir prasyaratnya selesai.
    - Task tidak dimulai sebelum `earliest`.
    - Task boleh dipecah ke beberapa sesi (D2), masing-masing minimal `min_session` menit
      (kecuali task itu sendiri lebih pendek).
    - Beban per hari dibatasi agar merata (D5): rata-rata menit per hari yang punya slot luang
      × DAILY_CAP_TOLERANCE. Jika batas itu membuat task tidak muat padahal masih ada waktu,
      batas dinaikkan bertahap.
    - Task yang tetap tidak muat (atau prasyaratnya tidak muat / dependensi melingkar) masuk
      `unscheduled` — tidak pernah dijadwalkan melewati slot yang diberikan.
    """
    tasks = list(tasks)
    slots = merge_intervals(slots)
    ordered, cyclic = _dependency_order(tasks)
    if not ordered or not slots:
        return ScheduleResult(unscheduled=sorted(t.task_number for t in tasks))

    total = sum(t.minutes for t in ordered)
    days = {s.start.date() for s in slots}
    max_day_free = max(sum(s.minutes for s in slots if s.start.date() == d) for d in days)
    cap = math.ceil(total / len(days) * DAILY_CAP_TOLERANCE)

    while True:
        result = _schedule_with_cap(ordered, slots, cap, min_session)
        if not result.unscheduled or cap >= max_day_free:
            break
        cap = min(max_day_free, cap + min_session)

    result.unscheduled = sorted(result.unscheduled + cyclic)
    return result


# ============================================================
# DETEKSI BENTROK (FR-5)
# ============================================================

@dataclass(frozen=True)
class BusyBlock:
    """Jam sibuk yang tidak boleh ditabrak.

    kind: "rutin" (kegiatan rutin mingguan), "agenda" (acara sekali-jalan), atau "task" (sesi task lain)
    label: nama yang ditampilkan ke user (mis. "Kuliah", "Task #3")
    """

    interval: Interval
    kind: str
    label: str


@dataclass(frozen=True)
class Conflict:
    candidate: Interval  # jadwal yang dicek
    blocking: BusyBlock  # yang ditabrak
    overlap: Interval  # bagian yang tumpang tindih

    @property
    def message(self) -> str:
        return (f"Bentrok dengan {self.blocking.label} "
                f"({self.overlap.start:%d/%m %H:%M}-{self.overlap.end:%H:%M}, {self.overlap.minutes} menit)")


def busy_blocks(
    start: datetime,
    end: datetime,
    routines: Iterable[WeeklyWindow] = (),
    agendas: Iterable[BusyBlock] = (),
    sessions: Iterable[Session] = (),
) -> list[BusyBlock]:
    """Kumpulkan semua jam sibuk di [start, end) dari kegiatan rutin, agenda, dan sesi task."""
    blocks = [BusyBlock(iv, "rutin", w.label or "kegiatan rutin")
              for w, iv in _expand_weekly_each(routines, start, end)]
    blocks += [a for a in agendas if a.interval.start < end and a.interval.end > start]
    blocks += [BusyBlock(s.interval, "task", f"Task #{s.task_number}")
               for s in sessions if s.interval.start < end and s.interval.end > start]
    return sorted(blocks, key=lambda b: b.interval.start)


def find_conflicts(candidate: Interval, blocks: Iterable[BusyBlock]) -> list[Conflict]:
    """
    Cek apakah satu jadwal bertabrakan dengan jam sibuk mana pun (FR-5).
    Bersentuhan di ujung (mis. 19:00-20:00 dan 20:00-21:00) tidak dianggap bentrok.

    Untuk memindahkan sesi secara manual: kirim `blocks` tanpa sesi yang sedang dipindah,
    supaya sesi itu tidak dianggap bentrok dengan posisi lamanya.
    """
    conflicts = []
    for b in blocks:
        start, end = max(candidate.start, b.interval.start), min(candidate.end, b.interval.end)
        if start < end:
            conflicts.append(Conflict(candidate, b, Interval(start, end)))
    return sorted(conflicts, key=lambda c: c.overlap.start)


def validate_schedule(sessions: Iterable[Session], blocks: Iterable[BusyBlock] = ()) -> list[Conflict]:
    """
    Cek seluruh jadwal: bentrok antar-sesi task, dan bentrok sesi dengan jam sibuk lain.
    Hasil kosong = jadwal aman (tidak ada double booking).
    """
    sessions = sorted(sessions, key=lambda s: s.interval.start)
    blocks = list(blocks)
    conflicts = []
    for i, s in enumerate(sessions):
        others = [BusyBlock(o.interval, "task", f"Task #{o.task_number}") for o in sessions[i + 1:]]
        conflicts += find_conflicts(s.interval, others + blocks)
    return conflicts
