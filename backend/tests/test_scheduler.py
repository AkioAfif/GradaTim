"""Unit tests untuk app/services/scheduler.py"""

from datetime import datetime, time

import pytest

from app.services.scheduler import (
    Interval,
    TaskToSchedule,
    WeeklyWindow,
    average_daily_minutes,
    expand_weekly,
    free_slots,
    merge_intervals,
    schedule_tasks,
    subtract_intervals,
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
