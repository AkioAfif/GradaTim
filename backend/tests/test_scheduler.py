"""Unit tests untuk app/services/scheduler.py"""

from datetime import datetime, time

import pytest

from app.services.scheduler import (
    BusyBlock,
    Interval,
    Session,
    TaskToSchedule,
    WeeklyWindow,
    average_daily_minutes,
    busy_blocks,
    expand_weekly,
    find_conflicts,
    free_slots,
    merge_intervals,
    schedule_tasks,
    subtract_intervals,
    validate_schedule,
)

# 5 Oktober 2026 = Senin
MON, TUE, WED, SAT, SUN = 0, 1, 2, 5, 6


def dt(day, hour, minute=0):
    return datetime(2026, 10, day, hour, minute)


def iv(day, h1, h2, m1=0, m2=0):
    return Interval(dt(day, h1, m1), dt(day, h2, m2))


# ------------------------------------------------------------
# VALIDASI
# ------------------------------------------------------------

def test_weekly_window_validation():
    with pytest.raises(ValueError):
        WeeklyWindow(7, time(9), time(10))
    with pytest.raises(ValueError):
        WeeklyWindow(MON, time(9), time(9))
    assert WeeklyWindow(MON, time(22), time(1)).minutes == 180  # lewat tengah malam


def test_interval_validation():
    with pytest.raises(ValueError):
        Interval(dt(5, 10), dt(5, 9))


# ------------------------------------------------------------
# OPERASI INTERVAL
# ------------------------------------------------------------

def test_merge_intervals_overlapping_and_touching():
    merged = merge_intervals([iv(5, 13, 14), iv(5, 9, 11), iv(5, 10, 12), iv(5, 12, 13)])
    assert merged == [iv(5, 9, 14)]


def test_subtract_intervals_splits_and_trims():
    free = [iv(5, 8, 17)]
    busy = [iv(5, 7, 9), iv(5, 12, 13), iv(5, 16, 18)]
    assert subtract_intervals(free, busy) == [iv(5, 9, 12), iv(5, 13, 16)]


def test_subtract_intervals_fully_covered():
    assert subtract_intervals([iv(5, 9, 10)], [iv(5, 8, 11)]) == []


# ------------------------------------------------------------
# EXPAND MINGGUAN
# ------------------------------------------------------------

def test_expand_weekly_repeats_each_week_and_clips():
    windows = [WeeklyWindow(MON, time(19), time(21))]
    # Senin 5 Okt 20:00 s/d Senin 12 Okt 20:00 → sisa Senin pertama + awal Senin kedua
    result = expand_weekly(windows, dt(5, 20), dt(12, 20))
    assert result == [iv(5, 20, 21), iv(12, 19, 20)]


def test_expand_weekly_multiple_windows_same_day_merged():
    windows = [WeeklyWindow(SAT, time(9), time(11)), WeeklyWindow(SAT, time(10), time(12))]
    assert expand_weekly(windows, dt(10, 0), dt(11, 0)) == [iv(10, 9, 12)]


def test_expand_weekly_crossing_midnight():
    windows = [WeeklyWindow(SUN, time(22), time(1))]  # Minggu 4 Okt 22:00 - Senin 01:00
    result = expand_weekly(windows, dt(5, 0), dt(5, 12))
    assert result == [Interval(dt(5, 0), dt(5, 1))]  # ekor dari hari sebelumnya ikut terhitung


# ------------------------------------------------------------
# FREE SLOTS
# ------------------------------------------------------------

AVAILABILITY = [
    WeeklyWindow(MON, time(8), time(17)),
    WeeklyWindow(TUE, time(19), time(21)),
    WeeklyWindow(SAT, time(9), time(12)),
]
ROUTINES = [
    WeeklyWindow(MON, time(10), time(12)),  # kuliah
    WeeklyWindow(SAT, time(9), time(10)),   # gym
]


def test_free_slots_subtracts_routines_and_busy():
    busy = [iv(5, 14, 15)]  # agenda sekali-jalan
    slots = free_slots(AVAILABILITY, dt(5, 0), dt(12, 0), ROUTINES, busy)
    assert slots == [
        iv(5, 8, 10), iv(5, 12, 14), iv(5, 15, 17),  # Senin
        iv(6, 19, 21),                               # Selasa
        iv(10, 10, 12),                              # Sabtu
    ]


def test_free_slots_starts_from_now():
    slots = free_slots(AVAILABILITY, dt(5, 16, 30), dt(7, 0))
    assert slots == [iv(5, 16, 17, m1=30), iv(6, 19, 21)]


def test_free_slots_drops_short_fragments():
    busy = [Interval(dt(5, 8, 10), dt(5, 16, 50))]  # sisa 8:00-8:10 dan 16:50-17:00
    assert free_slots([WeeklyWindow(MON, time(8), time(17))], dt(5, 0), dt(6, 0), busy=busy) == []


def test_free_slots_empty_range():
    assert free_slots(AVAILABILITY, dt(6, 0), dt(5, 0)) == []


# ------------------------------------------------------------
# RATA-RATA MENIT HARIAN (D6)
# ------------------------------------------------------------

def test_average_daily_minutes():
    # luang: Senin 540 + Selasa 120 + Sabtu 180 = 840 menit; rutin: 120 + 60 = 180 → 660 / 7 = 94
    assert average_daily_minutes(AVAILABILITY, ROUTINES) == 94
    assert average_daily_minutes([WeeklyWindow(SUN, time(22), time(1))]) == 180 // 7


# ------------------------------------------------------------
# PENEMPATAN TASK (FR-4)
# ------------------------------------------------------------

def T(number, minutes, deps=(), earliest=None):
    return TaskToSchedule(number, minutes, tuple(deps), earliest)


def sessions_of(result, number):
    return [s.interval for s in result.sessions if s.task_number == number]


def evening_slots(days=range(5, 10)):
    """Senin-Jumat 19:00-21:00 (120 menit/hari)."""
    return [iv(d, 19, 21) for d in days]


def test_schedule_respects_dependencies():
    tasks = [T(2, 60, deps=[1]), T(1, 60)]
    result = schedule_tasks(tasks, evening_slots())
    assert sessions_of(result, 2)[0].start >= sessions_of(result, 1)[-1].end
    assert result.unscheduled == []


def test_schedule_never_overlaps_and_stays_in_slots():
    slots = evening_slots()
    result = schedule_tasks([T(n, 45) for n in range(1, 9)], slots)
    intervals = sorted((s.interval for s in result.sessions), key=lambda i: i.start)
    for a, b in zip(intervals, intervals[1:]):
        assert a.end <= b.start
    for i in intervals:
        assert any(sl.start <= i.start and i.end <= sl.end for sl in slots)


def test_schedule_spreads_load_evenly():
    # 5 x 60 menit, 5 hari x 120 menit luang → tidak boleh semua ditumpuk di 2-3 hari pertama
    result = schedule_tasks([T(n, 60) for n in range(1, 6)], evening_slots())
    load = result.daily_load()
    assert len(load) >= 4
    assert max(load.values()) <= result.daily_cap_minutes < 120  # tidak memenuhi jam luang (D5)


def test_schedule_splits_long_task_across_days():
    result = schedule_tasks([T(1, 90)], [iv(5, 19, 20), iv(6, 19, 20)])
    parts = sessions_of(result, 1)
    assert len(parts) == 2
    assert sum(p.minutes for p in parts) == 90
    assert all(p.minutes >= 15 for p in parts)


def test_schedule_no_tiny_leftover_session():
    # slot pertama 50 menit untuk task 60 menit → jangan 50 + 10, tapi 45 + 15
    # (kedua slot di hari yang sama supaya batas beban harian tidak ikut membatasi)
    result = schedule_tasks([T(1, 60)], [Interval(dt(5, 19), dt(5, 19, 50)), iv(5, 20, 21)])
    assert [p.minutes for p in sessions_of(result, 1)] == [45, 15]


def test_schedule_short_task_allowed():
    result = schedule_tasks([T(1, 10)], evening_slots())
    assert sessions_of(result, 1)[0].minutes == 10


def test_schedule_respects_earliest():
    result = schedule_tasks([T(1, 30, earliest=dt(7, 0))], evening_slots())
    assert sessions_of(result, 1)[0].start == dt(7, 19)


def test_schedule_reports_tasks_that_do_not_fit():
    # 2 hari x 120 menit = 240 menit luang, butuh 300
    tasks = [T(1, 100), T(2, 100), T(3, 100, deps=[2])]
    result = schedule_tasks(tasks, evening_slots(days=[5, 6]))
    assert result.unscheduled == [3]
    assert sessions_of(result, 3) == []
    assert sum(s.interval.minutes for s in result.sessions) == 200


def test_schedule_dependent_of_unscheduled_task_is_unscheduled():
    tasks = [T(1, 700), T(2, 30, deps=[1])]  # luang total cuma 5 x 120 = 600 menit
    result = schedule_tasks(tasks, evening_slots())
    assert result.unscheduled == [1, 2]


def test_schedule_cyclic_dependencies_unscheduled():
    tasks = [T(1, 30, deps=[2]), T(2, 30, deps=[1]), T(3, 30)]
    result = schedule_tasks(tasks, evening_slots())
    assert result.unscheduled == [1, 2]
    assert sessions_of(result, 3)


def test_schedule_unknown_dependency_treated_as_done():
    result = schedule_tasks([T(5, 30, deps=[99])], evening_slots())
    assert result.unscheduled == []


def test_schedule_cap_raised_when_days_are_uneven():
    # 1 hari punya 3 jam, 4 hari lain cuma 15 menit → rata-rata kecil, tapi task 120 menit tetap harus muat
    slots = [iv(5, 9, 12)] + [Interval(dt(d, 19), dt(d, 19, 15)) for d in range(6, 10)]
    result = schedule_tasks([T(1, 120)], slots)
    assert result.unscheduled == []


def test_schedule_end_to_end_with_free_slots():
    slots = free_slots(AVAILABILITY, dt(5, 0), dt(12, 0), ROUTINES)
    result = schedule_tasks([T(1, 60), T(2, 90, deps=[1]), T(3, 45)], slots)
    assert result.unscheduled == []
    routine_busy = expand_weekly(ROUTINES, dt(5, 0), dt(12, 0))
    for s in result.sessions:
        assert all(s.interval.end <= r.start or s.interval.start >= r.end for r in routine_busy)


def test_schedule_empty_inputs():
    assert schedule_tasks([], evening_slots()).sessions == []
    assert schedule_tasks([T(1, 30)], []).unscheduled == [1]


# ------------------------------------------------------------
# DETEKSI BENTROK (FR-5)
# ------------------------------------------------------------

KULIAH = WeeklyWindow(MON, time(10), time(12), label="Kuliah")
RAPAT = BusyBlock(iv(6, 19, 20), "agenda", "Rapat himpunan")


def test_weekly_window_label_not_part_of_equality():
    assert WeeklyWindow(MON, time(10), time(12), label="Kuliah") == WeeklyWindow(MON, time(10), time(12))


def test_busy_blocks_collects_all_sources_with_labels():
    sessions = [Session(3, iv(7, 19, 20))]
    blocks = busy_blocks(dt(5, 0), dt(12, 0), [KULIAH], [RAPAT], sessions)
    assert [(b.kind, b.label) for b in blocks] == [
        ("rutin", "Kuliah"), ("agenda", "Rapat himpunan"), ("task", "Task #3"),
    ]


def test_busy_blocks_ignores_items_outside_range():
    blocks = busy_blocks(dt(7, 0), dt(8, 0), [KULIAH], [RAPAT], [Session(1, iv(9, 19, 20))])
    assert blocks == []


def test_find_conflicts_reports_overlap_and_label():
    blocks = busy_blocks(dt(5, 0), dt(12, 0), [KULIAH])
    conflicts = find_conflicts(Interval(dt(5, 11), dt(5, 13)), blocks)
    assert len(conflicts) == 1
    assert conflicts[0].overlap == iv(5, 11, 12)
    assert conflicts[0].message == "Bentrok dengan Kuliah (05/10 11:00-12:00, 60 menit)"


def test_find_conflicts_touching_is_not_conflict():
    blocks = busy_blocks(dt(5, 0), dt(12, 0), [KULIAH])
    assert find_conflicts(iv(5, 12, 13), blocks) == []
    assert find_conflicts(iv(5, 9, 10), blocks) == []


def test_find_conflicts_multiple_blocks():
    blocks = [BusyBlock(iv(6, 19, 20), "agenda", "A"), BusyBlock(iv(6, 20, 21), "task", "Task #1")]
    conflicts = find_conflicts(Interval(dt(6, 19, 30), dt(6, 20, 30)), blocks)
    assert [c.blocking.label for c in conflicts] == ["A", "Task #1"]


def test_manual_move_excluding_own_session():
    """User memindahkan sesi Task #1 sedikit lebih maju — tidak boleh bentrok dengan posisi lamanya."""
    sessions = [Session(1, iv(6, 19, 20)), Session(2, iv(6, 20, 21))]
    moving = sessions[0]
    others = [s for s in sessions if s is not moving]
    blocks = busy_blocks(dt(5, 0), dt(12, 0), sessions=others)
    assert find_conflicts(Interval(dt(6, 18, 30), dt(6, 19, 30)), blocks) == []
    assert [c.blocking.label for c in find_conflicts(Interval(dt(6, 19, 30), dt(6, 20, 30)), blocks)] == ["Task #2"]


def test_validate_schedule_detects_double_booking():
    sessions = [Session(1, iv(6, 19, 20)), Session(2, Interval(dt(6, 19, 30), dt(6, 20, 30))), Session(3, iv(7, 19, 20))]
    conflicts = validate_schedule(sessions, [RAPAT])
    labels = sorted(c.blocking.label for c in conflicts)
    # Task #1 vs Task #2, Task #1 vs Rapat, Task #2 vs Rapat
    assert labels == ["Rapat himpunan", "Rapat himpunan", "Task #2"]


def test_auto_schedule_has_no_conflicts():
    """Hasil penjadwal otomatis (FR-4) harus selalu lolos validasi bentrok (FR-5)."""
    start, end = dt(5, 0), dt(12, 0)
    existing = [Session(99, iv(5, 13, 14))]  # sesi dari goal lain
    blocks = busy_blocks(start, end, [KULIAH], [RAPAT], existing)
    slots = free_slots([WeeklyWindow(d, time(8), time(21)) for d in range(7)], start, end,
                       busy=[b.interval for b in blocks])
    result = schedule_tasks([T(n, 60, deps=[n - 1] if n > 1 else []) for n in range(1, 11)], slots)
    assert result.unscheduled == []
    assert validate_schedule(result.sessions, blocks) == []
