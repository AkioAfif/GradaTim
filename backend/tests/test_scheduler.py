"""Unit tests untuk app/services/scheduler.py"""

from datetime import datetime, time

import pytest

from app.services.scheduler import (
    Interval,
    WeeklyWindow,
    average_daily_minutes,
    expand_weekly,
    free_slots,
    merge_intervals,
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
