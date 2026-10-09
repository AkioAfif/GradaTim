"""Tes Settings (config.py) dan helper waktu (waktu.py)."""

from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import create_engine

from app.core import waktu
from app.core.config import Settings


def _settings(**kwargs) -> Settings:
    # _env_file=None: tes tidak boleh bergantung pada isi backend/.env
    return Settings(_env_file=None, **kwargs)


def test_jam_aktif_default():
    s = _settings()
    assert s.JAM_AKTIF_MULAI == time(6, 0)
    assert s.JAM_AKTIF_SELESAI == time(22, 0)


def test_jam_aktif_dibaca_dari_string_hh_mm():
    s = _settings(JAM_AKTIF_MULAI="07:30", JAM_AKTIF_SELESAI="21:00")
    assert s.JAM_AKTIF_MULAI == time(7, 30)
    assert s.JAM_AKTIF_SELESAI == time(21, 0)


def test_jam_aktif_dibaca_dari_env(monkeypatch):
    monkeypatch.setenv("JAM_AKTIF_MULAI", "05:45")
    assert _settings().JAM_AKTIF_MULAI == time(5, 45)


def test_url_postgresql_polos_memakai_driver_psycopg3():
    # requirements.txt hanya memasang psycopg (v3). SQLAlchemy >= 2.1 memetakan `postgresql://`
    # ke psycopg 3; jika versi SQLAlchemy turun ke 2.0, tes ini gagal (driver default psycopg2).
    engine = create_engine("postgresql://u:p@localhost/db")
    assert engine.dialect.driver == "psycopg"


def test_ke_wib_naif_mengonversi_utc():
    utc = datetime(2026, 10, 7, 12, 0, tzinfo=timezone.utc)
    assert waktu.ke_wib_naif(utc) == datetime(2026, 10, 7, 19, 0)


def test_ke_wib_naif_offset_lain():
    jepang = datetime(2026, 10, 7, 21, 0, tzinfo=timezone(timedelta(hours=9)))
    assert waktu.ke_wib_naif(jepang) == datetime(2026, 10, 7, 19, 0)


def test_ke_wib_naif_naive_tidak_diubah():
    naive = datetime(2026, 10, 7, 8, 0)
    assert waktu.ke_wib_naif(naive) is naive


def test_hari_ini_memakai_wib():
    assert isinstance(waktu.hari_ini(), date)
    assert waktu.hari_ini() == datetime.now(waktu.WIB).date()
