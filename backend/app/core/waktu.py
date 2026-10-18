"""Helper waktu. Semua datetime di DB adalah waktu lokal WIB tanpa timezone (naive)."""

from datetime import date, datetime, time, timedelta, timezone

# WIB tidak punya DST → offset tetap cukup (zoneinfo butuh paket tzdata di Windows)
WIB = timezone(timedelta(hours=7))


def ke_wib_naif(dt: datetime) -> datetime:
    """Datetime ber-timezone dikonversi ke WIB lalu tzinfo dibuang; datetime naive dianggap sudah WIB."""
    if dt.tzinfo is None or dt.utcoffset() is None:
        return dt
    return dt.astimezone(WIB).replace(tzinfo=None)


def hari_ini() -> date:
    """Tanggal hari ini di WIB. Panggil lewat modul (`waktu.hari_ini()`) agar mudah di-monkeypatch di tes."""
    return datetime.now(WIB).date()


def akhir_hari(d: date) -> datetime:
    """Deadline berupa tanggal disimpan sebagai akhir hari itu (kolom deadline bertipe DateTime)."""
    return datetime.combine(d, time(23, 59))
