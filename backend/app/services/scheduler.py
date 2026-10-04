"""Scheduling logic — penjadwalan otomatis task ke kalender (FR-4, FR-5, FR-11)

Fungsi murni tanpa database. Keputusan desain: docs/KEPUTUSAN_DESAIN_PENJADWALAN.md

Tahap 1 (modul ini): menghitung slot waktu luang konkret.
    jam luang mingguan (time_constraint)
    − kegiatan rutin mingguan (kuliah, gym, ...)
    − jam sibuk lain (agenda sekali-jalan, sesi task yang sudah terjadwal)
    = slot luang yang boleh diisi task

Semua waktu memakai datetime lokal (WIB) tanpa timezone.
"""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Iterable

MIN_SESSION_MINUTES = 15  # sisa slot di bawah ini tidak dipakai (lihat §7 dokumen desain)


@dataclass(frozen=True)
class WeeklyWindow:
    """Rentang jam yang berulang tiap minggu — bentuknya sama dengan time_constraint / kegiatan rutin.

    weekday: 0=Senin ... 6=Minggu (sama dengan TimeConstraint.hari_dalam_minggu dan date.weekday()).
    Jika end <= start, rentang dianggap melewati tengah malam (mis. 22:00-01:00).
    """

    weekday: int
    start: time
    end: time

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


def expand_weekly(windows: Iterable[WeeklyWindow], start: datetime, end: datetime) -> list[Interval]:
    """Ubah rentang mingguan jadi interval konkret yang beririsan dengan [start, end), lalu gabungkan."""
    windows = list(windows)
    intervals = []
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
                intervals.append(Interval(clipped_start, clipped_end))
        day += timedelta(days=1)
    return merge_intervals(intervals)


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
        availability: jam luang mingguan user (time_constraint)
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
